<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- Logo and Title -->
      <div class="auth-header">
        <div class="logo-glow">
          <img :src="logo" alt="Trading Platform" class="auth-logo" />
        </div>
        <h1 class="auth-title">LOBX</h1>
        <p class="auth-subtitle">Experimental Market Research Platform</p>
        <div class="auth-divider"></div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="auth-loading">
        <div class="spinner"></div>
        <p>{{ loadingMessage }}</p>
      </div>

      <!-- Admin Password Form (no LAB_TOKEN in URL) -->
      <div v-else class="auth-form">
        <h2 class="form-title">Admin Access</h2>
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
            <span v-if="loginLoading" class="btn-loading">
              <span class="btn-spinner"></span>
              Authenticating...
            </span>
            <span v-else>Sign In</span>
          </button>
        </form>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="error-message">
        <span>{{ errorMessage }}</span>
        <button class="error-close" @click="errorMessage = ''">&times;</button>
      </div>

      <!-- Footer -->
      <div class="auth-footer">
        <span>Royal Holloway, University of London</span>
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
  // Auto-detect LAB token in URL (prefer ?LAB=, fallback to legacy ?LAB_TOKEN=)
  const labToken = route.query.LAB || route.query.LAB_TOKEN || sessionStore.labToken || sessionStore.loadLabToken()
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
  position: relative;
  overflow: hidden;
}

.auth-container {
  width: 100%;
  max-width: 420px;
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-6);
  box-shadow: var(--shadow-lg);
  position: relative;
  z-index: 1;
  animation: slideUp 0.4s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.auth-header {
  text-align: center;
  margin-bottom: var(--space-6);
}

.logo-glow {
  display: inline-block;
  padding: var(--space-3);
  border-radius: var(--radius-xl);
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  margin-bottom: var(--space-4);
}

.auth-logo {
  width: 56px;
  height: 56px;
  display: block;
}

.auth-title {
  font-family: var(--font-mono);
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  color: var(--color-text-bright);
  margin: 0 0 var(--space-1) 0;
  letter-spacing: var(--tracking-widest);
}

.auth-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.auth-divider {
  width: 40px;
  height: 2px;
  background: var(--color-primary);
  opacity: 0.3;
  margin: var(--space-4) auto 0;
  border-radius: 1px;
}

.auth-loading {
  text-align: center;
  padding: var(--space-8) 0;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 2px solid var(--color-border-strong);
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
  font-family: var(--font-mono);
}

.auth-form {
  text-align: center;
}

.form-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4) 0;
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
}

.input-group {
  margin-bottom: var(--space-4);
  text-align: left;
}

.input-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  margin-bottom: var(--space-1-5);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.input-field {
  width: 100%;
  padding: var(--space-3);
  font-size: var(--text-base);
  font-family: var(--font-mono);
  color: var(--color-text-primary);
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border-strong);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input-field:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}

.input-field::placeholder {
  color: var(--color-text-muted);
  font-family: var(--font-family);
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  font-family: var(--font-family);
  border-radius: var(--radius-md);
  border: var(--border-width) solid transparent;
  cursor: pointer;
  transition: all var(--transition-smooth);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-glow);
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--color-text-inverse);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
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
  border: var(--border-width) solid rgba(220, 38, 38, 0.2);
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

.auth-footer {
  text-align: center;
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: var(--border-width) solid var(--color-border-light);
}

.auth-footer span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: var(--tracking-wide);
}

@media (max-width: 480px) {
  .auth-container {
    padding: var(--space-6) var(--space-4);
  }
  .auth-logo {
    width: 48px;
    height: 48px;
  }
  .auth-title {
    font-size: var(--text-3xl);
  }
}
</style>
