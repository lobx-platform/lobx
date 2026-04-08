/**
 * NavigationService — imperative navigation actions.
 *
 * Route-guard logic (getRedirectForStatus, step validation) has moved
 * to router/guards.js. This service only handles explicit user actions
 * like "after login", "start trading", "next step", etc.
 */
import router from '@/router'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { ONBOARDING_ROUTES } from '@/router/guards'

const READY_PAGE_INDEX = 7

export const NavigationService = {
  /**
   * After successful login — determine where to send the user.
   */
  async afterLogin() {
    const sessionStore = useSessionStore()
    const authStore = useAuthStore()

    try {
      await sessionStore.syncFromBackend()
    } catch (e) {
      console.warn('Failed to sync session from backend:', e)
    }

    if (authStore.isAdmin) {
      sessionStore.setOnboardingStep(READY_PAGE_INDEX)
      sessionStore.setStatus('waiting')
      return router.push({ name: 'ready' })
    }

    const savedStep = sessionStore.onboardingStep || 0
    if (savedStep >= READY_PAGE_INDEX) {
      sessionStore.setStatus('waiting')
      return router.push({ name: 'ready' })
    }

    sessionStore.setStatus('onboarding')
    const routeName = ONBOARDING_ROUTES[savedStep] || 'consent'
    return router.push({ name: routeName })
  },

  async nextOnboardingStep() {
    const sessionStore = useSessionStore()
    const currentStep = sessionStore.onboardingStep
    if (currentStep >= READY_PAGE_INDEX) return
    const nextStep = currentStep + 1
    sessionStore.setOnboardingStep(nextStep)
    return router.push({ name: ONBOARDING_ROUTES[nextStep] })
  },

  async prevOnboardingStep() {
    const sessionStore = useSessionStore()
    const currentStep = sessionStore.onboardingStep
    if (currentStep <= 0) return
    const prevStep = currentStep - 1
    sessionStore.setOnboardingStep(prevStep)
    return router.push({ name: ONBOARDING_ROUTES[prevStep] })
  },

  async startTrading() {
    const sessionStore = useSessionStore()
    const { useTraderStore } = await import('@/store/app')
    const traderStore = useTraderStore()

    const result = await traderStore.startTradingMarket()
    if (result && result.all_ready) {
      await this.onMarketStarted()
    } else {
      sessionStore.setStatus('waiting')
    }
  },

  async onMarketStarted(marketId = null) {
    const sessionStore = useSessionStore()
    if (marketId) sessionStore.marketId = marketId
    sessionStore.setStatus('trading')
    return router.push({ name: 'trading' })
  },

  async onTradingEnded() {
    const sessionStore = useSessionStore()
    const { useWebSocketStore } = await import('@/store/websocket')
    const wsStore = useWebSocketStore()

    sessionStore.setStatus('summary')
    sessionStore.incrementMarketsCompleted()
    wsStore.disconnect()
    return router.push({ name: 'summary' })
  },

  async startNextMarket() {
    const sessionStore = useSessionStore()
    const { useTraderStore } = await import('@/store/app')
    const traderStore = useTraderStore()

    try {
      const axios = (await import('@/api/axios')).default
      await axios.post('/session/reset-for-new-market')
    } catch (error) {
      console.warn('[Navigation] Failed to reset backend session:', error)
    }

    traderStore.clearStore()
    sessionStore.resetForNewMarket()
    return router.push({ name: 'ready' })
  },

  async goToAdmin() {
    const authStore = useAuthStore()
    if (!authStore.isAdmin) return router.push({ name: 'auth' })
    return router.push({ name: 'admin' })
  },

  async logout() {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()
    const { useTraderStore } = await import('@/store/app')
    const traderStore = useTraderStore()
    const { useWebSocketStore } = await import('@/store/websocket')
    const wsStore = useWebSocketStore()

    wsStore.disconnect()
    traderStore.clearStore()
    sessionStore.reset()
    authStore.logout()
    return router.push({ name: 'auth' })
  },

  /**
   * Called when the study is complete (after final questionnaire).
   * Currently a no-op — the UI handles this inline.
   */
  completeStudy() {
    // no-op
  },
}

export default NavigationService
