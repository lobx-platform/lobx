<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor" class="pulse-icon">mdi-rocket-launch</v-icon>
        <h2 class="text-h4 gradient-text">Ready to Trade</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Duration Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-clock-outline</v-icon>
                  <span class="text-h6">Duration</span>
                </div>
                <p class="text-body-1">
                  Trade for <span class="highlight-text">{{ marketDuration }} minutes</span>
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Progress Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-progress-check</v-icon>
                  <span class="text-h6">Market Progress</span>
                </div>
                <div class="d-flex justify-space-between align-center mb-2">
                  <span>Markets You Have Played:</span>
                  <span class="highlight-text">{{ currentMarket }}</span>
                </div>
                <div class="d-flex justify-space-between align-center mb-3">
                  <span>Markets You Can Still Play:</span>
                  <span class="highlight-text">{{ remainingMarkets }}</span>
                </div>
                <v-progress-linear
                  v-if="!isAdmin"
                  :value="marketProgress"
                  height="8"
                  rounded
                  striped
                  color="primary"
                ></v-progress-linear>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Parameters Table Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-table</v-icon>
                  <span class="text-h6">Trading Parameters</span>
                </div>

                <v-data-table
                  :headers="headers"
                  :items="items"
                  hide-default-footer
                  disable-pagination
                  class="parameters-table"
                ></v-data-table>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>

      <!-- Action Buttons -->
      <div class="action-buttons mt-6">
        <v-btn
          @click="startTrading"
          :loading="isLoading"
          :disabled="!canStartTrading"
          class="start-button"
          size="x-large"
          elevation="2"
        >
          <v-icon left class="mr-2">mdi-play-circle-outline</v-icon>
          {{ startButtonText }}
        </v-btn>

        <v-btn
          @click="handleLogout"
          color="error"
          variant="text"
          class="logout-button mt-2"
          :disabled="isLoading"
        >
          <v-icon left class="mr-1">mdi-logout</v-icon>
          Logout
        </v-btn>
      </div>
    </v-container>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useTraderStore } from '@/store/app'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { storeToRefs } from 'pinia'
import NavigationService from '@/services/navigation'

const traderStore = useTraderStore()
const sessionStore = useSessionStore()
const authStore = useAuthStore()

const { goalMessage } = storeToRefs(traderStore)

const props = defineProps({
  traderAttributes: Object,
  iconColor: String,
})

const isLoading = ref(false)

// Watch for market started signal from WebSocket
watch(
  () => traderStore.shouldRedirectToTrading,
  (shouldRedirect) => {
    if (shouldRedirect) {
      traderStore.setShouldRedirectToTrading(false)
      NavigationService.onMarketStarted()
    }
  }
)

// Also watch isTradingStarted as a backup
watch(
  () => traderStore.isTradingStarted,
  (started) => {
    if (started && !traderStore.isWaitingForOthers) {
      NavigationService.onMarketStarted()
    }
  }
)

const marketDuration = computed(() => {
  return (
    traderStore.gameParams?.trading_day_duration ||
    traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration ||
    'Loading...'
  )
})

const initialShares = computed(() => props.traderAttributes?.shares ?? 'Loading...')
const initialCash = computed(() => props.traderAttributes?.cash ?? 'Loading...')

const canStartTrading = computed(() => {
  return !!props.traderAttributes
})

const startButtonText = computed(() => {
  if (isLoading.value) return 'Starting...'
  if (traderStore.isWaitingForOthers) return 'Waiting for other traders...'
  return 'Start Trading'
})

const headers = [
  { text: 'Parameter', value: 'parameter', align: 'left' },
  { text: 'Value', value: 'value', align: 'left' },
]

const items = computed(() => {
  const baseItems = [
    { parameter: 'Initial Shares', value: initialShares.value },
    {
      parameter: 'Initial Cash',
      value: initialCash.value ? `${initialCash.value} Liras` : 'Loading...',
    },
  ]

  const goalValue = props.traderAttributes?.goal
  if (goalValue !== undefined && goalValue !== null) {
    if (goalValue > 0) {
      baseItems.push({ parameter: 'Shares to Buy', value: goalValue })
    } else if (goalValue < 0) {
      baseItems.push({ parameter: 'Shares to Sell', value: Math.abs(goalValue) })
    }
  }

  return baseItems
})

const startTrading = async () => {
  if (!canStartTrading.value || isLoading.value) {
    return
  }

  isLoading.value = true
  
  try {
    await NavigationService.startTrading()
    
    // Give WebSocket time to respond
    // Navigation will happen via the watcher when shouldRedirectToTrading becomes true
    // or when isTradingStarted becomes true
    
    // Fallback: check after a delay if we should navigate
    setTimeout(() => {
      if (traderStore.isTradingStarted && !traderStore.isWaitingForOthers) {
        NavigationService.onMarketStarted()
      }
      // Keep loading state if still waiting for others
      if (!traderStore.isWaitingForOthers) {
        isLoading.value = false
      }
    }, 500)
  } catch (error) {
    console.error('Failed to start trading:', error)
    isLoading.value = false
  }
}

const handleLogout = async () => {
  await NavigationService.logout()
}

const currentMarket = computed(() => {
  return props.traderAttributes?.all_attributes?.historical_markets_count || 
         sessionStore.marketsCompleted || 
         0
})

const maxMarketsPerHuman = computed(() => {
  return props.traderAttributes?.all_attributes?.params?.max_markets_per_human || 
         sessionStore.maxMarkets || 
         4
})

const isAdmin = computed(() => {
  return props.traderAttributes?.all_attributes?.is_admin || authStore.isAdmin || false
})

const remainingMarkets = computed(() => {
  if (isAdmin.value) return '∞'
  return maxMarketsPerHuman.value - currentMarket.value
})

const marketProgress = computed(() => {
  if (isAdmin.value) return 100
  return (currentMarket.value / maxMarketsPerHuman.value) * 100
})
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
.parameters-table {
  border-radius: 8px;
  overflow: hidden;
}

.start-button {
  width: 100%;
  max-width: 400px;
  height: 56px;
  font-size: 1.1rem;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  background: var(--color-primary) !important;
  color: var(--color-text-inverse) !important;
  transition: all 0.3s ease;
}

.start-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow);
}

.action-buttons {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 2rem;
}

.logout-button {
  font-size: 0.9rem;
  text-transform: none;
}
</style>
