<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- Title -->
      <div class="auth-header">
        <h1 class="auth-title">LOBX</h1>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="auth-loading">
        <div class="spinner"></div>
        <p>{{ loadingMessage }}</p>
      </div>

      <!-- Admin Password Form (no LAB_TOKEN in URL) -->
      <div v-else class="auth-form">
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
            <span v-if="loginLoading">Authenticating...</span>
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
}

.auth-container {
  width: 100%;
  max-width: 360px;
}

.auth-header {
  text-align: center;
  margin-bottom: 4rem;
}

.auth-title {
  font-family: var(--font-mono);
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: 0.2em;
}

.auth-loading {
  text-align: center;
  padding: var(--space-8) 0;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-text-primary);
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
  text-align: left;
}

.input-group {
  margin-bottom: var(--space-4);
}

.input-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
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
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
}

.input-field:focus {
  outline: none;
  border-color: var(--color-primary);
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
  font-weight: var(--font-medium);
  font-family: var(--font-family);
  border-radius: var(--radius-md);
  border: var(--border-width) solid transparent;
  cursor: pointer;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
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
  border: var(--border-width) solid rgba(203, 36, 49, 0.2);
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
  margin-top: 4rem;
}

.auth-footer span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: var(--tracking-wide);
}

@media (max-width: 480px) {
  .auth-header {
    margin-bottom: 3rem;
  }
  .auth-title {
    font-size: var(--text-3xl);
  }
  .auth-footer {
    margin-top: 3rem;
  }
}
</style>
