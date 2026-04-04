// Centralized navigation service - all route transitions go through here
import router from '@/router'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { useTraderStore } from '@/store/app'
import { useWebSocketStore } from '@/store/websocket'

// Onboarding pages in order (0-6 are instruction pages, 7 is ready page)
const ONBOARDING_ROUTES = [
  'consent',      // 0
  'welcome',      // 1
  'platform',     // 2
  'setup',        // 3
  'earnings',     // 4
  'participants', // 5
  'questions',    // 6
  'ready'         // 7 - special: this is the "completed onboarding" page
]

// Ready page is treated differently - it's the gateway to trading
const READY_PAGE_INDEX = 7

export const NavigationService = {
  /**
   * Get the appropriate redirect based on session status
   */
  getRedirectForStatus(status) {
    switch (status) {
      case 'unauthenticated':
      case 'unknown':
        return { name: 'auth' }
      case 'authenticated':
      case 'onboarding':
        return { name: 'consent' }
      case 'waiting':
        return { name: 'ready' }
      case 'trading':
        return { name: 'trading' }
      case 'summary':
        return { name: 'summary' }
      case 'complete':
        return { name: 'summary' }
      default:
        return { name: 'auth' }
    }
  },

  /**
   * Get the route name for a given step index
   */
  getRouteForStep(step) {
    if (step < 0) return ONBOARDING_ROUTES[0]
    if (step >= ONBOARDING_ROUTES.length) return ONBOARDING_ROUTES[READY_PAGE_INDEX]
    return ONBOARDING_ROUTES[step]
  },

  /**
   * Get the step index for a given route name
   */
  getStepForRoute(routeName) {
    const index = ONBOARDING_ROUTES.indexOf(routeName)
    return index >= 0 ? index : 0
  },

  /**
   * After successful login - determine where to send the user
   *
   * Logic:
   * - Admin users skip onboarding entirely, go to ready page
   * - Load user's saved progress
   * - If they completed onboarding (step >= 7), go to ready page
   * - Otherwise, resume at their saved step
   */
  async afterLogin() {
    const sessionStore = useSessionStore()
    const authStore = useAuthStore()

    console.log('[Navigation] afterLogin called')
    console.log('[Navigation] Current sessionStore.onboardingStep:', sessionStore.onboardingStep)

    try {
      await sessionStore.syncFromBackend()
    } catch (e) {
      console.warn('Failed to sync session from backend:', e)
    }

    // Admin users skip onboarding entirely
    if (authStore.isAdmin) {
      console.log('[Navigation] Admin user, skipping to ready page')
      sessionStore.setOnboardingStep(READY_PAGE_INDEX)
      sessionStore.setStatus('waiting')
      return router.push({ name: 'ready' })
    }

    // Use session store's current step (synced from backend or persisted)
    const savedStep = sessionStore.onboardingStep || 0
    console.log('[Navigation] savedStep:', savedStep)

    // Navigate to the appropriate page
    if (savedStep >= READY_PAGE_INDEX) {
      sessionStore.setStatus('waiting')
      return router.push({ name: 'ready' })
    } else {
      sessionStore.setStatus('onboarding')
      return router.push({ name: this.getRouteForStep(savedStep) })
    }
  },

  /**
   * Navigate to next onboarding step
   */
  async nextOnboardingStep() {
    const sessionStore = useSessionStore()
    const currentStep = sessionStore.onboardingStep

    if (currentStep >= READY_PAGE_INDEX) return

    const nextStep = currentStep + 1
    sessionStore.setOnboardingStep(nextStep)

    const nextRoute = this.getRouteForStep(nextStep)
    return router.push({ name: nextRoute })
  },

  /**
   * Navigate to previous onboarding step
   */
  async prevOnboardingStep() {
    const sessionStore = useSessionStore()
    const currentStep = sessionStore.onboardingStep

    if (currentStep <= 0) return

    const prevStep = currentStep - 1
    sessionStore.setOnboardingStep(prevStep)
    return router.push({ name: this.getRouteForStep(prevStep) })
  },

  /**
   * When user clicks "Start Trading" from ready page
   */
  async startTrading() {
    const sessionStore = useSessionStore()
    const traderStore = useTraderStore()

    try {
      const result = await traderStore.startTradingMarket()
      if (result && result.all_ready) {
        // Market started immediately, navigate directly
        await this.onMarketStarted()
      } else {
        sessionStore.setStatus('waiting')
        // Navigation will happen via WebSocket 'market_started' event
      }
    } catch (error) {
      console.error('Failed to start trading:', error)
      throw error
    }
  },

  /**
   * Called by WebSocket when market starts - navigate to trading
   */
  async onMarketStarted(marketId = null) {
    const sessionStore = useSessionStore()

    if (marketId) {
      sessionStore.marketId = marketId
    }
    sessionStore.setStatus('trading')

    return router.push({ name: 'trading' })
  },

  /**
   * When trading session ends - navigate to summary
   */
  async onTradingEnded() {
    const sessionStore = useSessionStore()
    const wsStore = useWebSocketStore()

    sessionStore.setStatus('summary')
    sessionStore.incrementMarketsCompleted()
    wsStore.disconnect()

    return router.push({ name: 'summary' })
  },

  /**
   * Start next market (from summary page)
   */
  async startNextMarket() {
    const sessionStore = useSessionStore()
    const traderStore = useTraderStore()

    // Note: canStartNewMarket is already checked by the caller (goToNextMarket)

    // Tell backend to clean up the finished market session
    try {
      const axios = (await import('@/api/axios')).default
      await axios.post('/session/reset-for-new-market')
      console.log('[Navigation] Backend session reset successful')
    } catch (error) {
      console.warn('[Navigation] Failed to reset backend session:', error)
      // Continue anyway - the backend might already be cleaned up
    }

    // Reset trader state for new market
    traderStore.clearStore()

    // Reset session for new market
    sessionStore.resetForNewMarket()
    console.log('[Navigation] After resetForNewMarket, status:', sessionStore.status)

    console.log('[Navigation] Navigating to ready page')
    return router.push({ name: 'ready' })
  },

  /**
   * Navigate to admin panel
   */
  async goToAdmin() {
    const authStore = useAuthStore()

    if (!authStore.isAdmin) {
      return router.push({ name: 'auth' })
    }

    return router.push({ name: 'admin' })
  },

  /**
   * Logout and reset all state
   */
  async logout() {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()
    const traderStore = useTraderStore()
    const wsStore = useWebSocketStore()

    // Disconnect WebSocket
    wsStore.disconnect()

    // Clear all stores
    traderStore.clearStore()
    sessionStore.reset()
    authStore.logout()


    return router.push({ name: 'auth' })
  },

  /**
   * Handle recovery after page refresh
   */
  async recoverSession() {
    const sessionStore = useSessionStore()
    const authStore = useAuthStore()

    // If not authenticated, go to auth
    if (!authStore.isAuthenticated) {
      sessionStore.setStatus('unauthenticated')
      return { name: 'auth' }
    }

    // Try to sync from backend
    try {
      await sessionStore.syncFromBackend()
    } catch (e) {
      console.warn('Using persisted session state')
    }

    return this.getRedirectForStatus(sessionStore.status)
  }
}

export default NavigationService
