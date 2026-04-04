import axios from 'axios'
import router from '@/router'

const instance = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,
})

// Helper to show global error notifications
const showGlobalError = async (message) => {
  try {
    const { useUIStore } = await import('@/store/ui')
    const uiStore = useUIStore()
    uiStore.showError(message)
  } catch (e) {
    console.error('Could not show error notification:', e)
  }
}

instance.interceptors.request.use(
  async (config) => {
    try {
      const { useAuthStore } = await import('@/store/auth')
      const authStore = useAuthStore()

      // Lab token
      if (authStore.labToken) {
        config.headers.Authorization = `Lab ${authStore.labToken}`
      }
      // Admin password as Bearer token
      else if (authStore.adminToken) {
        config.headers.Authorization = `Bearer ${authStore.adminToken}`
      }
      return config
    } catch (error) {
      console.error('Error setting auth header:', error)
      return Promise.reject(error)
    }
  },
  (error) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || error.response.data?.message || ''

      if (status === 401) {
        router.push('/')
        return Promise.reject(error)
      }

      if (status === 403 && detail.includes('Maximum number of markets reached')) {
        error.message = 'You have reached the maximum number of allowed markets.'
        showGlobalError(error.message)
      } else if (status >= 500) {
        error.message = detail || 'Server error occurred. Please try again later.'
        showGlobalError(error.message)
      } else if (status >= 400 && status !== 401) {
        error.message = detail || 'An error occurred'
        if (status !== 400 || !detail.includes('validation')) {
          showGlobalError(error.message)
        }
      } else {
        error.message = detail || 'An error occurred'
      }
    } else if (error.request) {
      error.message = 'No response received from server'
      showGlobalError('Unable to connect to server. Please check your connection.')
    } else {
      error.message = 'Error setting up the request'
    }
    return Promise.reject(error)
  }
)

export default instance
