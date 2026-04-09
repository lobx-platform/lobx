/**
 * Router guards — single authority for navigation decisions.
 *
 * Uses Vue Router 4 return-based guards (no deprecated next() callback).
 * Replaces the old dual-authority system (guards.js + NavigationService).
 */
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'

// Single source of truth for onboarding step -> route name mapping
export const ONBOARDING_ROUTES = [
  'consent',      // 0
  'welcome',      // 1
  'platform',     // 2
  'setup',        // 3
  'earnings',     // 4
  'participants', // 5
  'questions',    // 6
  'ready',        // 7
]

/**
 * Determine the correct destination for a user based on session status.
 * Replaces NavigationService.getRedirectForStatus().
 */
export function resolveDestination(sessionStore) {
  switch (sessionStore.status) {
    case 'unauthenticated':
    case 'unknown':
      return { name: 'auth' }
    case 'authenticated':
    case 'onboarding': {
      // Respect the user's onboarding progress (fixes consent bounce-back)
      const step = sessionStore.onboardingStep || 0
      const routeName = ONBOARDING_ROUTES[Math.min(step, ONBOARDING_ROUTES.length - 1)]
      return { name: routeName }
    }
    case 'waiting':
      return { name: 'ready' }
    case 'trading':
      return { name: 'trading' }
    case 'summary':
    case 'complete':
      return { name: 'summary' }
    default:
      return { name: 'auth' }
  }
}

/**
 * Setup all navigation guards on the router.
 */
export function setupGuards(router) {
  router.beforeEach(async (to, from) => {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()

    // 0. Restore state on cold start (first navigation after page refresh)
    if (!sessionStore._restored) {
      sessionStore.loadFromLocalStorage()
      // Also restore per-user onboarding step
      const uid = authStore.user?.uid
      if (uid) {
        try {
          const saved = localStorage.getItem(`onboarding_step_${uid}`)
          if (saved !== null) {
            const step = parseInt(saved, 10)
            if (!isNaN(step) && step >= 0 && step <= 7) {
              sessionStore.onboardingStep = step
              sessionStore.hasCompletedOnboarding = step >= 7
            }
          }
        } catch (e) {
          // Ignore
        }
      }
      sessionStore._restored = true
    }

    // 1. Handle new login params in URL — if different user, clear old state
    const labParam = to.query.LAB || to.query.LAB_TOKEN
    const prolificParam = to.query.PROLIFIC_PID
    if (labParam || prolificParam) {
      const newTraderId = labParam
        ? `HUMAN_LAB_${labParam}`
        : `HUMAN_PROLIFIC_${prolificParam}`
      if (authStore.traderId && authStore.traderId !== newTraderId) {
        // Different user — clear everything and let auth page handle fresh login
        sessionStore.reset()
        authStore.logout()
      }
      if (labParam) {
        sessionStore.setLoginToken(labParam)
      }
    }

    // 2. Guest-only routes — redirect authenticated users
    if (to.meta.requiresGuest && authStore.isAuthenticated) {
      return resolveDestination(sessionStore)
    }

    // 3. Auth required — redirect unauthenticated users
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      return {
        name: 'auth',
        query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined,
      }
    }

    // 4. Admin required
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
      return { name: 'auth' }
    }

    // 5. Active market required (trading page)
    if (to.meta.requiresActiveMarket) {
      if (sessionStore.status !== 'trading') {
        try {
          await sessionStore.syncFromBackend()
        } catch (e) {
          // Use local state
        }

        if (sessionStore.status !== 'trading') {
          return resolveDestination(sessionStore)
        }
      }
    }

    // 6. Onboarding step validation
    if (to.meta.step !== undefined && to.meta.requiresAuth) {
      const targetStep = to.meta.step
      const currentProgress = sessionStore.onboardingStep

      // Completed users can't go back to earlier pages
      if (currentProgress >= 7 && targetStep < 7) {
        return { name: 'ready' }
      }

      // Can't skip ahead (current step + 1 max)
      if (targetStep > currentProgress + 1) {
        const allowedRoute = ONBOARDING_ROUTES[currentProgress] || 'consent'
        return { name: allowedRoute }
      }
    }

    // 7. Session sync for protected routes (non-blocking — fire and forget)
    if (to.meta.requiresSession && !sessionStore.isSyncing) {
      sessionStore.syncFromBackend().catch(() => {})
    }

    // Allow navigation (return undefined = proceed)
  })

  // NOTE: afterEach status-setting hook is intentionally REMOVED.
  // Status should be set explicitly by actions (login, startTrading, onTradingEnded),
  // not inferred from the current route name.
}

export default setupGuards
