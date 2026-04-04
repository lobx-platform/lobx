<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- Logo and Title -->
      <div class="auth-header">
        <img :src="logo" alt="Trading Platform" class="auth-logo" />
        <h1 class="auth-title">Trading Platform</h1>
        <p class="auth-subtitle">Experimental Market Research</p>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="auth-loading">
        <div class="spinner"></div>
        <p>{{ loadingMessage }}</p>
      </div>

      <!-- Admin Password Form (no LAB_TOKEN in URL) -->
      <div v-else class="auth-form">
        <h2 class="form-title">Admin Login</h2>
        <form @submit.prevent="handleAdminLogin">
          <div class="input-group">
            <label class="input-label">Password</label>
            <input
              v-model="password"
              type="password"
              class="input-field"
              placeholder="Enter admin password"
              :disabled="loginLoading"
              required
            />
          </div>
          <button type="submit" class="btn btn-primary" :disabled="loginLoading">
            {{ loginLoading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="error-message">
        <span>{{ errorMessage }}</span>
        <button class="error-close" @click="errorMessage = ''">&times;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'
import NavigationService from '@/services/navigation'
import logo from '@/assets/lobx_logo.svg'

const route = useRoute()
const authStore = useAuthStore()
const sessionStore = useSessionStore()

const errorMessage = ref('')
const isLoading = ref(false)
const loadingMessage = ref('Loading...')
const loginLoading = ref(false)
const password = ref('')

onMounted(async () => {
  // Auto-detect LAB_TOKEN in URL or localStorage
  const labToken = route.query.LAB_TOKEN || sessionStore.labToken || sessionStore.loadLabToken()
  if (labToken) {
    isLoading.value = true
    loadingMessage.value = 'Signing in with lab token...'
    try {
      sessionStore.setLabToken(labToken)
      await authStore.labLogin(labToken)
      await NavigationService.afterLogin()
      return
    } catch (error) {
      console.error('Lab auto-login failed:', error)
      errorMessage.value = error.message || 'Failed to sign in with lab token'
      isLoading.value = false
    }
  }

  // Auto-detect Prolific params in URL
  const prolificPID = route.query.PROLIFIC_PID
  if (prolificPID) {
    isLoading.value = true
    loadingMessage.value = 'Signing in via Prolific...'
    try {
      await authStore.prolificLogin(prolificPID, route.query.STUDY_ID, route.query.SESSION_ID)
      await NavigationService.afterLogin()
      return
    } catch (error) {
      console.error('Prolific auto-login failed:', error)
      errorMessage.value = error.message || 'Failed to sign in via Prolific'
      isLoading.value = false
    }
  }
})

const handleAdminLogin = async () => {
  if (!password.value) {
    errorMessage.value = 'Please enter a password'
    return
  }
  loginLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.adminPasswordLogin(password.value)
    await NavigationService.goToAdmin()
  } catch (error) {
    console.error('Admin login error:', error)
    errorMessage.value = error.message || 'Invalid password'
  } finally {
    loginLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: var(--space-4);
}

.auth-container {
  width: 100%;
  max-width: 400px;
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  box-shadow: var(--shadow-lg);
}

.auth-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.auth-logo {
  width: 80px;
  height: 80px;
  margin-bottom: var(--space-4);
}

.auth-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1) 0;
}

.auth-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.auth-loading {
  text-align: center;
  padding: var(--space-8) 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto var(--space-4);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auth-loading p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  margin: 0;
}

.auth-form {
  text-align: center;
}

.form-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4) 0;
}

.input-group {
  margin-bottom: var(--space-4);
  text-align: left;
}

.input-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

.input-field {
  width: 100%;
  padding: var(--space-3);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input-field:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  border: var(--border-width) solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.error-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--color-error-light);
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.error-close {
  background: none;
  border: none;
  color: var(--color-error);
  font-size: var(--text-lg);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

@media (max-width: 480px) {
  .auth-container {
    padding: var(--space-6);
  }
  .auth-logo {
    width: 64px;
    height: 64px;
  }
}
</style>
