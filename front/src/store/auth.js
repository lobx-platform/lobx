import { defineStore } from 'pinia'
import axios from '@/api/axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAdmin: false,
    traderId: null,
    marketId: null,
    labToken: null,
    adminToken: null,
    loginInProgress: false,
  }),
  actions: {
    syncToSessionStore() {
      try {
        import('./session').then(({ useSessionStore }) => {
          const sessionStore = useSessionStore()
          if (this.traderId && sessionStore.traderId !== this.traderId) {
            sessionStore.traderId = this.traderId
          }
        })
      } catch (e) {
        // Session store not available yet
      }
    },

    async labLogin(labToken) {
      if (this.loginInProgress) return

      try {
        this.loginInProgress = true
        const response = await axios.post(`/user/login?LAB_TOKEN=${labToken}`)

        if (!response.data.data || !response.data.data.trader_id) {
          throw new Error('No trader ID received')
        }

        const data = response.data.data
        this.user = {
          uid: data.uid || `lab_${labToken}`,
          email: data.email || 'lab@lab.local',
          displayName: 'Lab Participant',
          isLab: true,
        }
        this.isAdmin = false
        this.traderId = data.trader_id
        this.labToken = data.lab_token || labToken
        this.syncToSessionStore()
      } catch (error) {
        console.error('Lab login error:', error)
        this.user = null
        throw new Error(error.message || 'Failed to login with lab token')
      } finally {
        this.loginInProgress = false
      }
    },

    async prolificLogin(prolificPID, studyID, sessionID) {
      if (this.loginInProgress) return

      try {
        this.loginInProgress = true
        const params = new URLSearchParams({ PROLIFIC_PID: prolificPID })
        if (studyID) params.set('STUDY_ID', studyID)
        if (sessionID) params.set('SESSION_ID', sessionID)

        const response = await axios.post(`/user/login?${params.toString()}`)

        if (!response.data.data || !response.data.data.trader_id) {
          throw new Error('No trader ID received')
        }

        const data = response.data.data
        this.user = {
          uid: prolificPID,
          email: `${prolificPID}@prolific`,
          displayName: 'Prolific Participant',
          isProlific: true,
          prolificData: { PROLIFIC_PID: prolificPID, STUDY_ID: studyID, SESSION_ID: sessionID },
        }
        this.isAdmin = false
        this.traderId = data.trader_id
        this.syncToSessionStore()
      } catch (error) {
        console.error('Prolific login error:', error)
        this.user = null
        throw new Error(error.message || 'Failed to login via Prolific')
      } finally {
        this.loginInProgress = false
      }
    },

    async adminPasswordLogin(password) {
      try {
        this.adminToken = password
        const response = await axios.post('/admin/login', { password })

        this.user = {
          uid: 'admin',
          email: 'admin@local',
          displayName: 'Admin',
        }
        this.isAdmin = response.data.data?.is_admin ?? true
      } catch (error) {
        this.adminToken = null
        console.error('Admin login error:', error)
        throw new Error(error.message || 'Failed to login as admin')
      }
    },

    logout() {
      this.loginInProgress = false
      this.user = null
      this.isAdmin = false
      this.traderId = null
      this.marketId = null
      this.labToken = null
      this.adminToken = null
      localStorage.removeItem('auth')
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.user,
    isLabUser: (state) => !!state.user?.isLab,
  },
  persist: {
    enabled: true,
    strategies: [
      {
        storage: localStorage,
        paths: ['isAdmin', 'traderId', 'marketId', 'labToken', 'adminToken'],
      },
    ],
  },
})
