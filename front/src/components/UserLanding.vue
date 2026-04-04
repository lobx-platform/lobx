<template>
  <div class="landing-container">
    <Toaster position="top-center" theme="dark" :visibleToasts="3" />

    <!-- Modern gradient background -->
    <div class="gradient-bg"></div>

    <!-- Floating elements for visual interest -->
    <div class="floating-elements">
      <div class="floating-shape floating-shape-1"></div>
      <div class="floating-shape floating-shape-2"></div>
      <div class="floating-shape floating-shape-3"></div>
    </div>

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

            <!-- Header section with enhanced styling -->
            <div class="modern-header">
              <div v-motion-pop-visible-once :delay="400" class="icon-container">
                <component :is="getCurrentIcon()" :size="40" class="page-icon" />
              </div>
              <h1 v-motion-slide-visible-once-right :delay="600" class="page-title">
                {{ currentPageTitle }}
              </h1>
            </div>

            <!-- Content area with enhanced spacing -->
            <div v-motion-fade-visible-once :delay="800" class="content-area">
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

.gradient-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(ellipse at 30% 20%, rgba(34, 211, 238, 0.06) 0%, transparent 50%),
              radial-gradient(ellipse at 70% 80%, rgba(168, 85, 247, 0.04) 0%, transparent 50%);
  z-index: -2;
}

.floating-elements {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: -1;
  pointer-events: none;
}

.floating-shape {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.05), transparent);
  animation: float 20s infinite ease-in-out;
}

.floating-shape-1 {
  width: 300px;
  height: 300px;
  top: 10%;
  left: -150px;
  animation-delay: 0s;
}

.floating-shape-2 {
  width: 200px;
  height: 200px;
  top: 60%;
  right: -100px;
  animation-delay: -7s;
}

.floating-shape-3 {
  width: 150px;
  height: 150px;
  bottom: 20%;
  left: 20%;
  animation-delay: -14s;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }
  33% {
    transform: translateY(-30px) rotate(120deg);
  }
  66% {
    transform: translateY(30px) rotate(240deg);
  }
}

.modern-card {
  background: var(--color-bg-surface);
  backdrop-filter: blur(20px);
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
  background: linear-gradient(90deg, var(--color-primary), #A855F7, var(--color-bid));
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
  background: linear-gradient(90deg, var(--color-primary), #A855F7);
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
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border-strong);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-glow-sm);
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

.nav-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transition: left 0.6s;
}

.nav-btn:hover::before {
  left: 100%;
}

.nav-btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-glow-sm);
}

.nav-btn-primary:hover:not(.disabled) {
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

.nav-btn-secondary {
  background: var(--color-bg-elevated);
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
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.3);
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
