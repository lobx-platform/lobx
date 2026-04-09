import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const routes = [
  // Public - Auth page
  {
    path: '/',
    name: 'auth',
    component: () => import('@/components/Auth.vue'),
    meta: { requiresGuest: true },
    props: (route) => ({
      prolificPID: route.query.PROLIFIC_PID,
      studyID: route.query.STUDY_ID,
      sessionID: route.query.SESSION_ID,
    }),
  },

  // Legacy register route - redirect to auth
  {
    path: '/register',
    redirect: { name: 'auth' }
  },

  // Protected - Onboarding flow (simplified URLs without IDs)
  {
    path: '/onboarding',
    component: () => import('@/components/UserLanding.vue'),
    meta: { requiresAuth: true, requiresSession: true },
    children: [
      { 
        path: '', 
        redirect: { name: 'consent' } 
      },
      { 
        path: 'consent', 
        name: 'consent', 
        component: () => import('@/components/pages/0.vue'), 
        meta: { step: 0, requiresAuth: true } 
      },
      { 
        path: 'welcome', 
        name: 'welcome', 
        component: () => import('@/components/pages/1.vue'), 
        meta: { step: 1, requiresAuth: true } 
      },
      { 
        path: 'platform', 
        name: 'platform', 
        component: () => import('@/components/pages/2.vue'), 
        meta: { step: 2, requiresAuth: true } 
      },
      { 
        path: 'setup', 
        name: 'setup', 
        component: () => import('@/components/pages/3.vue'), 
        meta: { step: 3, requiresAuth: true } 
      },
      { 
        path: 'earnings', 
        name: 'earnings', 
        component: () => import('@/components/pages/4.vue'), 
        meta: { step: 4, requiresAuth: true } 
      },
      { 
        path: 'participants', 
        name: 'participants', 
        component: () => import('@/components/pages/6.vue'), 
        meta: { step: 5, requiresAuth: true } 
      },
      { 
        path: 'questions', 
        name: 'questions', 
        component: () => import('@/components/pages/7.vue'), 
        meta: { step: 6, requiresAuth: true } 
      },
      { 
        path: 'ready', 
        name: 'ready', 
        component: () => import('@/components/pages/8.vue'), 
        meta: { step: 7, requiresAuth: true } 
      },
    ],
  },

  // Legacy onboarding routes with IDs - redirect to new routes
  {
    path: '/onboarding/:marketId/:traderUuid',
    redirect: to => {
      // Extract the child path if present
      const childPath = to.params.pathMatch || ''
      if (childPath) {
        return `/onboarding/${childPath}`
      }
      return '/onboarding/consent'
    },
    children: [
      { path: 'consent', redirect: { name: 'consent' } },
      { path: 'welcome', redirect: { name: 'welcome' } },
      { path: 'platform', redirect: { name: 'platform' } },
      { path: 'setup', redirect: { name: 'setup' } },
      { path: 'earnings', redirect: { name: 'earnings' } },
      { path: 'participants', redirect: { name: 'participants' } },
      { path: 'questions', redirect: { name: 'questions' } },
      { path: 'practice', redirect: { name: 'ready' } },
    ]
  },

  // Protected - Trading dashboard
  {
    path: '/trading',
    name: 'trading',
    component: () => import('@/components/TradingDashboard.vue'),
    meta: { requiresAuth: true, requiresActiveMarket: true },
  },

  // Legacy trading route with IDs - redirect to new route
  {
    path: '/trading/:traderUuid/:marketId',
    redirect: { name: 'trading' }
  },

  // Protected - Market summary
  {
    path: '/summary',
    name: 'summary',
    component: () => import('@/components/market/MarketSummary.vue'),
    meta: { requiresAuth: true },
  },

  // Legacy summary route with ID - redirect to new route
  {
    path: '/summary/:traderUuid',
    redirect: { name: 'summary' }
  },

  // Admin - Dashboard
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/components/market/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },

  // Legacy admin route
  {
    path: '/MarketCreator',
    redirect: { name: 'admin' }
  },

  // Logout — clears all state and redirects to auth
  {
    path: '/logout',
    name: 'logout',
    beforeEnter: async () => {
      const { useAuthStore } = await import('@/store/auth')
      const { useSessionStore } = await import('@/store/session')
      const { useTraderStore } = await import('@/store/app')
      const { disconnectSocket } = await import('@/socket')

      disconnectSocket()
      useTraderStore().clearStore()
      useSessionStore().reset()
      useAuthStore().logout()
      localStorage.clear()

      return { name: 'auth' }
    },
  },

  // Catch-all - redirect to auth
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'auth' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Setup navigation guards
setupGuards(router)

export default router
