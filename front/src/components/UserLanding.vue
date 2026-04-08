<template>
  <div class="landing-container">
    <Toaster position="top-center" theme="light" :visibleToasts="3" />

    <v-container fluid class="fill-height pa-0 relative">
      <v-row justify="center" align="center" class="fill-height">
        <v-col cols="12" md="10" lg="8">
          <div v-motion-slide-visible-once-bottom :delay="200" class="modern-card">
            <!-- Progress indicator -->
            <div class="progress-indicator">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${((currentPageIndex + 1) / pages.length) * 100}%` }"
                ></div>
              </div>
              <span class="progress-text"> {{ currentPageIndex + 1 }} of {{ pages.length }} </span>
            </div>

            <!-- Header -->
            <div class="modern-header">
              <h1 class="page-title">{{ currentPageTitle }}</h1>
            </div>

            <div class="content-area">
              <router-view
                :traderAttributes="traderAttributes"
                :iconColor="deepBlueColor"
                @update:canProgress="handleProgress"
              />
            </div>

            <!-- Enhanced navigation -->
            <div
              v-if="currentRouteName !== 'consent'"
              v-motion-fade
              :initial="{ opacity: 0 }"
              :enter="{ opacity: 1, transition: { delay: 500 } }"
              class="navigation-area"
            >
              <button
                @click="prevPage"
                :disabled="isFirstPage"
                class="nav-btn nav-btn-secondary"
                :class="{ disabled: isFirstPage }"
              >
                <ChevronLeft :size="20" />
                Previous
              </button>

              <button
                @click="nextPage"
                :disabled="isLastPage || shouldDisableNext"
                class="nav-btn nav-btn-primary"
                :class="{ disabled: isLastPage || shouldDisableNext }"
              >
                Next
                <ChevronRight :size="20" />
              </button>
            </div>
          </div>
        </v-col>
      </v-row>
    </v-container>
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
import {
  ClipboardCheck,
  Handshake,
  Monitor,
  Settings,
  DollarSign,
  Users,
  HelpCircle,
  GraduationCap,
  ChevronLeft,
  ChevronRight,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const traderStore = useTraderStore()

const { traderAttributes } = storeToRefs(traderStore)

const pages = [
  { name: 'consent', title: 'Research Participant Consent Form', icon: 'ClipboardCheck' },
  { name: 'welcome', title: 'Welcome', icon: 'Handshake' },
  { name: 'platform', title: 'Trading Platform', icon: 'Monitor' },
  { name: 'setup', title: 'Setup', icon: 'Settings' },
  { name: 'earnings', title: 'Your Earnings', icon: 'DollarSign' },
  { name: 'participants', title: 'Other Participants', icon: 'Users' },
  { name: 'questions', title: 'Control Questions', icon: 'HelpCircle' },
  { name: 'ready', title: 'Ready to Trade', icon: 'GraduationCap' },
]

// Icon mapping
const iconComponents = {
  ClipboardCheck,
  Handshake,
  Monitor,
  Settings,
  DollarSign,
  Users,
  HelpCircle,
  GraduationCap,
}

const getCurrentIcon = () => {
  const iconName = pages[currentPageIndex.value]?.icon
  return iconComponents[iconName] || ClipboardCheck
}

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
  position: relative;
  overflow-x: hidden;
  background: var(--color-bg-page);
}

.modern-card {
  background: var(--color-bg-surface);
  border-radius: var(--radius-xl);
  border: var(--border-width) solid var(--color-border);
  box-shadow: var(--shadow-lg);
  padding: 2rem;
  position: relative;
  overflow: hidden;
}

.modern-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--color-primary), #7C3AED, var(--color-bid));
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.progress-indicator {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--color-bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), #7C3AED);
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-medium);
  min-width: fit-content;
  letter-spacing: var(--tracking-wide);
}

.modern-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: var(--border-width) solid var(--color-border);
}

.icon-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  background: var(--color-primary-light);
  border: var(--border-width) solid var(--color-primary-muted);
  border-radius: var(--radius-xl);
}

.page-icon {
  color: var(--color-primary);
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-text-bright);
  line-height: 1.2;
  margin: 0;
  -webkit-text-fill-color: unset;
  background: none;
}

.content-area {
  margin-bottom: 2.5rem;
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
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: var(--radius-lg);
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  font-family: var(--font-family);
}

.nav-btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.nav-btn-primary:hover:not(.disabled) {
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.nav-btn-secondary {
  background: var(--color-bg-surface);
  color: var(--color-text-secondary);
  border: var(--border-width) solid var(--color-border-strong);
}

.nav-btn-secondary:hover:not(.disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.nav-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.nav-btn-skip {
  background: var(--color-warning);
  color: var(--color-text-inverse);
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
}

.nav-btn-skip:hover {
  transform: translateY(-1px);
}

.relative {
  position: relative;
}

/* Responsive design */
@media (max-width: 768px) {
  .modern-card {
    margin: 1rem;
    padding: 1.5rem;
    border-radius: var(--radius-lg);
  }

  .modern-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .navigation-area {
    flex-direction: column;
    gap: 1rem;
  }

  .nav-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
