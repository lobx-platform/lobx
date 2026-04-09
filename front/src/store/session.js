// Session state management - single source of truth for user flow state
import { defineStore } from 'pinia'
import axios from '@/api/axios'

export const useSessionStore = defineStore('session', {
  state: () => ({
    // Core session state
    // 'unknown' | 'unauthenticated' | 'authenticated' | 'onboarding' | 'waiting' | 'trading' | 'summary' | 'complete'
    status: 'unknown',
    
    // IDs
    traderId: null,
    marketId: null,
    
    // Onboarding progress (0-7, where 7 = ready to trade)
    onboardingStep: 0,
    hasCompletedOnboarding: false,
    
    // Market progress
    marketsCompleted: 0,
    maxMarkets: 4,
    
    // Flags
    isSyncing: false,
    lastSyncTime: null,

    // Login token for auto-re-login (lab token string, e.g. "T1_P1")
    loginToken: null,
  }),

  getters: {
    canTrade: (state) => state.status === 'trading',
    canStartNewMarket: (state) => state.marketsCompleted < state.maxMarkets,
    isLastMarket: (state) => state.marketsCompleted >= state.maxMarkets,
    isLabUser: (state) => !!state.loginToken,
    
    // Get the route name for current onboarding step
    currentOnboardingRoute: (state) => {
      const stepRoutes = ['consent', 'welcome', 'platform', 'setup', 'earnings', 'participants', 'questions', 'ready']
      return stepRoutes[state.onboardingStep] || 'consent'
    },
  },

  actions: {
    // Sync state from backend - call this on app init and after key transitions
    // Note: onboardingStep is managed by frontend (per-user localStorage), not backend
    async syncFromBackend() {
      if (this.isSyncing) return this.status

      try {
        this.isSyncing = true
        const response = await axios.get('/session/status')
        const data = response.data.data || response.data

        // Don't overwrite onboardingStep - it's managed by frontend per-user localStorage
        this.$patch({
          status: data.status || 'authenticated',
          traderId: data.trader_id,
          marketId: data.market_id,
          marketsCompleted: data.markets_completed || 0,
          maxMarkets: data.max_markets || 4,
          lastSyncTime: Date.now(),
        })

        this.saveToLocalStorage()
        return this.status
      } catch (error) {
        if (error.response?.status === 401) {
          this.status = 'unauthenticated'
        }
        throw error
      } finally {
        this.isSyncing = false
      }
    },

    // Set status locally (for optimistic updates)
    setStatus(newStatus) {
      this.status = newStatus
      this.saveToLocalStorage()
    },

    // Update onboarding progress
    setOnboardingStep(step) {
      this.onboardingStep = step
      this.hasCompletedOnboarding = step >= 7
      this.saveToLocalStorage()
      this.savePerUserOnboardingStep()
    },

    // Increment onboarding step
    advanceOnboarding() {
      if (this.onboardingStep < 7) {
        this.onboardingStep++
        this.hasCompletedOnboarding = this.onboardingStep >= 7
        this.saveToLocalStorage()
        this.savePerUserOnboardingStep()
      }
    },

    // Save onboarding step per-user (for Prolific users to resume at exact page)
    savePerUserOnboardingStep() {
      try {
        // Dynamically import to avoid circular dependency
        import('./auth').then(({ useAuthStore }) => {
          const authStore = useAuthStore()
          if (authStore.user?.uid) {
            localStorage.setItem(`onboarding_step_${authStore.user.uid}`, this.onboardingStep.toString())
          }
        })
      } catch (e) {
        // Auth store not available
      }
    },

    // Store login token (lab token string for auto-re-login)
    setLoginToken(token) {
      this.loginToken = token
      this.saveToLocalStorage()
    },

    // Load login token
    loadLoginToken() {
      return this.loginToken
    },

    // Called when market is completed
    incrementMarketsCompleted() {
      this.marketsCompleted++
      this.saveToLocalStorage()
    },

    // Reset for new market
    resetForNewMarket() {
      this.marketId = null
      this.status = 'waiting'
      this.saveToLocalStorage()
    },

    // Full reset (logout)
    reset() {
      this.$patch({
        status: 'unauthenticated',
        traderId: null,
        marketId: null,
        onboardingStep: 0,
        hasCompletedOnboarding: false,
        marketsCompleted: 0,
        isSyncing: false,
        lastSyncTime: null,
        loginToken: null,
      })
      this.saveToLocalStorage()
    },

    // Manual localStorage persistence (since pinia-plugin-persistedstate may not be installed)
    saveToLocalStorage() {
      const dataToSave = {
        traderId: this.traderId,
        marketId: this.marketId,
        status: this.status,
        onboardingStep: this.onboardingStep,
        hasCompletedOnboarding: this.hasCompletedOnboarding,
        marketsCompleted: this.marketsCompleted,
        maxMarkets: this.maxMarkets,
        loginToken: this.loginToken,
      }
      localStorage.setItem('session_store', JSON.stringify(dataToSave))
    },

    // Load from localStorage on init
    loadFromLocalStorage() {
      try {
        const stored = localStorage.getItem('session_store')
        if (stored) {
          const data = JSON.parse(stored)
          this.$patch(data)
        }
      } catch (e) {
        console.warn('Failed to load session from localStorage:', e)
      }
    },
  },

  persist: {
    pick: [
      'traderId',
      'marketId',
      'status',
      'onboardingStep',
      'hasCompletedOnboarding',
      'marketsCompleted',
      'maxMarkets',
      'loginToken',
    ],
  }
})
