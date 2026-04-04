// Router navigation guards
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'
import NavigationService from '@/services/navigation'

// Onboarding step routes in order
const ONBOARDING_ROUTES = ['consent', 'welcome', 'platform', 'setup', 'earnings', 'participants', 'questions', 'ready']

/**
 * Setup all navigation guards on the router
 */
export function setupGuards(router) {
  router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()

    // 1. Handle Lab token in URL - store for auto-login
    if (to.query.LAB_TOKEN) {
      sessionStore.setLabToken(to.query.LAB_TOKEN)
    }

    // 2. Guest-only routes (login page) - redirect authenticated users
    if (to.meta.requiresGuest && authStore.isAuthenticated) {
      // Let NavigationService handle where to go based on user's progress
      const redirect = NavigationService.getRedirectForStatus(sessionStore.status)
      return next(redirect)
    }

    // 3. Auth required - redirect unauthenticated users to login
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      return next({
        name: 'auth',
        query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined
      })
    }

    // 4. Admin required
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
      return next({ name: 'auth' })
    }

    // 5. Active market required (for trading page)
    if (to.meta.requiresActiveMarket) {
      if (sessionStore.status !== 'trading') {
        try {
          await sessionStore.syncFromBackend()
        } catch (e) {
          // Use local state
        }

        if (sessionStore.status !== 'trading') {
          const redirect = NavigationService.getRedirectForStatus(sessionStore.status)
          return next(redirect)
        }
      }
    }

    // 6. Onboarding step validation
    if (to.meta.step !== undefined && to.meta.requiresAuth) {
      const targetStep = to.meta.step
      const currentProgress = sessionStore.onboardingStep

      // Users who completed onboarding (step 7) should stay on ready page
      // They can't go back to earlier onboarding pages
      if (currentProgress >= 7 && targetStep < 7) {
        return next({ name: 'ready' })
      }

      // Prevent skipping ahead (can only go to current step or next step)
      if (targetStep > currentProgress + 1) {
        const allowedRoute = ONBOARDING_ROUTES[currentProgress] || 'consent'
        return next({ name: allowedRoute })
      }
    }

    // 7. Session sync for protected routes (non-blocking)
    if (to.meta.requiresSession && !sessionStore.isSyncing) {
      sessionStore.syncFromBackend().catch(() => {})
    }

    next()
  })

  // After each navigation, update session status based on current route
  router.afterEach((to, from) => {
    const sessionStore = useSessionStore()

    if (to.name === 'trading') {
      sessionStore.setStatus('trading')
    } else if (to.name === 'summary') {
      sessionStore.setStatus('summary')
    } else if (to.name === 'ready') {
      sessionStore.setStatus('waiting')
    } else if (ONBOARDING_ROUTES.includes(to.name) && to.name !== 'ready') {
      sessionStore.setStatus('onboarding')
    }
  })
}

export default setupGuards
