<template>
  <div class="landing-container">
    <Toaster position="top-center" theme="light" :visibleToasts="3" />

    <div class="landing-content">
      <!-- Progress indicator -->
      <div class="progress-indicator">
        <span class="progress-text">{{ currentPageIndex + 1 }} / {{ pages.length }}</span>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: `${((currentPageIndex + 1) / pages.length) * 100}%` }"
          ></div>
        </div>
      </div>

      <!-- Header -->
      <div class="page-header">
        <h1 class="page-title">{{ currentPageTitle }}</h1>
      </div>

      <div class="content-area">
        <router-view
          :traderAttributes="traderAttributes"
          :iconColor="deepBlueColor"
          @update:canProgress="handleProgress"
        />
      </div>

      <!-- Navigation -->
      <div
        v-if="currentRouteName !== 'consent'"
        class="navigation-area"
      >
        <button
          @click="prevPage"
          :disabled="isFirstPage"
          class="nav-btn nav-btn-secondary"
        >
          Previous
        </button>

        <button
          @click="nextPage"
          :disabled="isLastPage || shouldDisableNext"
          class="nav-btn nav-btn-primary"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTraderStore } from '@/store/app'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import NavigationService from '@/services/navigation'
import { Toaster } from 'vue-sonner'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const traderStore = useTraderStore()

const { traderAttributes } = storeToRefs(traderStore)

const pages = [
  { name: 'consent', title: 'Research Participant Consent Form' },
  { name: 'welcome', title: 'Welcome' },
  { name: 'platform', title: 'LOBX Platform' },
  { name: 'setup', title: 'Setup' },
  { name: 'earnings', title: 'Your Earnings' },
  { name: 'participants', title: 'Other Participants' },
  { name: 'questions', title: 'Control Questions' },
  { name: 'ready', title: 'Ready to Trade' },
]

const currentPageIndex = computed(() => {
  const index = pages.findIndex((page) => page.name === route.name)
  return index >= 0 ? index : 0
})

const currentPageTitle = computed(() => {
  return pages[currentPageIndex.value]?.title || ''
})

const currentRouteName = computed(() => route.name)
const isFirstPage = computed(() => currentPageIndex.value === 0)
const isLastPage = computed(() => currentPageIndex.value === pages.length - 1)

// Navigation using the service
const nextPage = () => {
  if (!isLastPage.value && !shouldDisableNext.value) {
    NavigationService.nextOnboardingStep()
  }
}

const prevPage = () => {
  if (!isFirstPage.value) {
    NavigationService.prevOnboardingStep()
  }
}

// Progress tracking
const canProgressFromQuestions = ref(false)
const consentGiven = ref(false)

const handleProgress = (value) => {
  if (currentRouteName.value === 'consent') {
    consentGiven.value = value
  } else if (currentRouteName.value === 'questions') {
    canProgressFromQuestions.value = value
  }
}

const shouldDisableNext = computed(() => {
  if (currentRouteName.value === 'consent') {
    return !consentGiven.value
  }
  return currentRouteName.value === 'questions' && !canProgressFromQuestions.value
})

// Initialize trader data
onMounted(async () => {
  const traderId = sessionStore.traderId || authStore.traderId

  if (traderId) {
    try {
      await traderStore.initializeTrader(traderId)
      await traderStore.initializeTradingSystemWithPersistentSettings()
      await traderStore.getTraderAttributes(traderId)
    } catch (error) {
      console.error('Error initializing trader:', error)
    }
  } else {
    console.error('No trader ID available')
  }
})

// Watch for route changes to reset progress flags
watch(currentRouteName, (newRoute, oldRoute) => {
  if (oldRoute === 'questions') {
    canProgressFromQuestions.value = false
  }

  // Mark onboarding as complete when reaching ready page
  if (newRoute === 'ready') {
    sessionStore.setOnboardingStep(7)
  }
})

const deepBlueColor = ref('deep-blue')
</script>

<style scoped>
.landing-container {
  min-height: 100vh;
  background: var(--color-bg-page);
  display: flex;
  justify-content: center;
  padding: 3rem 1.5rem;
}

.landing-content {
  width: 100%;
  max-width: 720px;
}

.progress-indicator {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.progress-bar {
  flex: 1;
  height: 2px;
  background: var(--color-border);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-text-primary);
  transition: width 0.3s ease;
}

.progress-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  min-width: fit-content;
  letter-spacing: var(--tracking-wide);
}

.page-header {
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: var(--border-width) solid var(--color-border);
}

.page-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  line-height: var(--leading-tight);
  margin: 0;
}

.content-area {
  margin-bottom: 3rem;
  min-height: 300px;
}

.navigation-area {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1.5rem;
  border-top: var(--border-width) solid var(--color-border);
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border: var(--border-width) solid transparent;
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  cursor: pointer;
  font-family: var(--font-family);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.nav-btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.nav-btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.nav-btn-secondary {
  background: var(--color-bg-surface);
  color: var(--color-text-secondary);
  border-color: var(--color-border);
}

.nav-btn-secondary:hover:not(:disabled) {
  color: var(--color-text-primary);
  border-color: var(--color-border-strong);
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .landing-container {
    padding: 2rem 1rem;
  }

  .page-title {
    font-size: var(--text-xl);
  }

  .navigation-area {
    gap: 1rem;
  }
}
</style>
