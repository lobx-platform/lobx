<template>
  <div class="trading-dashboard" v-show="isInitialized">
    <v-app>
      <!-- Add error alert at the top -->
      <v-alert
        v-if="showErrorAlert"
        type="error"
        closable
        class="ma-4"
        style="position: fixed; top: 0; left: 50%; transform: translateX(-50%); z-index: 1000"
      >
        Connection error. Please refresh the page.
        <v-btn color="white" variant="text" class="ml-4" @click="refreshPage"> Refresh Now </v-btn>
      </v-alert>

      <v-app-bar app elevation="2" color="white" height="auto" class="dynamic-header">
        <v-container fluid class="py-2">
          <v-row align="center" no-gutters>
            <v-col cols="auto">
              <h1 class="dashboard-title">
                <TrendingUp :size="28" class="title-icon" />
                Trading Dashboard
              </h1>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto" class="dashboard-stats">
              <!-- Modern role chip -->
              <div class="role-chip-modern" :class="roleColor">
                {{ roleDisplay.text }}
              </div>
              <div class="stats-chips">
                <div class="stat-chip pnl-chip">
                  <DollarSign :size="16" class="chip-icon" />
                  <span class="chip-label">PnL:</span>
                  <span class="chip-value">{{ pnl }}</span>
                </div>
                <div class="stat-chip shares-chip">
                  <Package :size="16" class="chip-icon" />
                  <span class="chip-label">Shares:</span>
                  <span class="chip-value">{{ initial_shares }} {{ formatDelta }}</span>
                </div>
                <div class="stat-chip cash-chip">
                  <Banknote :size="16" class="chip-icon" />
                  <span class="chip-label">Cash:</span>
                  <span class="chip-value">{{ cash }}</span>
                </div>
                <div class="stat-chip traders-chip">
                  <Users :size="16" class="chip-icon" />
                  <span class="chip-label">Traders:</span>
                  <span class="chip-value"
                    >{{ currentHumanTraders }} / {{ expectedHumanTraders }}</span
                  >
                </div>
              </div>
              <div v-if="hasGoal" class="goal-chip-modern" :class="getGoalMessageClass">
                <div class="goal-content">
                  <component :is="getGoalIcon()" :size="16" class="goal-icon" />
                  <span class="goal-type-text">{{ goalTypeText }}</span>
                </div>
                <div class="progress-container">
                  <div class="progress-bar-modern">
                    <div
                      class="progress-fill-modern"
                      :style="{ width: `${goalProgressPercentage}%` }"
                    ></div>
                  </div>
                  <span class="progress-text"
                    >{{ Math.abs(goalProgress) }}/{{ Math.abs(goal) }}</span
                  >
                </div>
              </div>
              <div class="time-chip">
                <Clock :size="16" class="chip-icon" />
                <vue-countdown
                  v-if="remainingTime"
                  :time="remainingTime * 1000"
                  v-slot="{ minutes, seconds }"
                >
                  {{ minutes }}:{{ seconds.toString().padStart(2, '0') }}
                </vue-countdown>
                <span v-else>Waiting to start</span>
              </div>
            </v-col>
          </v-row>
        </v-container>
      </v-app-bar>

      <v-main class="grey lighten-4 dynamic-main">
        <v-container fluid class="pa-4">
          <!-- Modified waiting screen -->
          <v-row v-if="!isTradingStarted" justify="center" align="center" style="height: 80vh">
            <v-col cols="12" md="6" class="text-center">
              <v-card elevation="2" class="pa-6">
                <v-card-title class="text-h4 mb-4">Waiting for Traders</v-card-title>
                <v-card-text>
                  <p class="text-h6 mb-4">
                    {{ currentHumanTraders }} out of {{ expectedHumanTraders }} traders have joined
                  </p>
                  <p class="subtitle-1 mb-4">
                    Your Role:
                    <v-chip :color="roleColor" text-color="white" small>
                      <v-icon left small>{{ roleIcon }}</v-icon>
                      {{ roleDisplay.text }}
                    </v-chip>
                  </p>
                  <v-progress-circular
                    :size="70"
                    :width="7"
                    color="primary"
                    indeterminate
                  ></v-progress-circular>
                  <p class="text--secondary mt-4">
                    <v-icon small color="grey">mdi-refresh</v-icon>
                    If waiting too long, you can refresh the page to try again
                  </p>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
          <v-row v-else>
            <!-- 3x2 Grid Layout -->
            <v-col cols="12" md="4" class="d-flex flex-column">
              <v-card class="mb-4 tool-card" elevation="2">
                <v-card-title class="tool-title">
                  <History :size="20" class="tool-icon" />
                  Your Trades
                </v-card-title>
                <v-card-text class="pa-0">
                  <OrderHistory :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
              <v-card class="mb-4 tool-card" elevation="2">
                <v-card-title class="tool-title">
                  <Info :size="20" class="tool-icon" />
                  Market Info
                </v-card-title>
                <v-card-text class="pa-0">
                  <MarketMessages :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
            </v-col>
            
            <v-col cols="12" md="4" class="d-flex flex-column">
              <v-card class="mb-4 tool-card" elevation="2">
                <v-card-title class="tool-title">
                  <BarChart3 :size="20" class="tool-icon" />
                  Buy-Sell Chart
                </v-card-title>
                <v-card-text class="pa-0">
                  <BidAskDistribution :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
              <v-card class="mb-4 tool-card" elevation="2">
                <v-card-title class="tool-title">
                  <List :size="20" class="tool-icon" />
                  Passive Orders
                </v-card-title>
                <v-card-text class="pa-0">
                  <ActiveOrders :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
            </v-col>
            
            <v-col cols="12" md="4" class="d-flex flex-column">
              <v-card class="mb-4 tool-card price-history-card" elevation="2">
                <v-card-title class="tool-title">
                  <LineChart :size="20" class="tool-icon" />
                  Market Trade Price History   
                </v-card-title>
                <v-card-text class="pa-0">
                  <PriceHistory :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
              <v-card class="mb-4 tool-card" elevation="2">
                <v-card-title class="tool-title">
                  <Calculator :size="20" class="tool-icon" />
                  Trading Panel
                </v-card-title>
                <v-card-text class="pa-0">
                  <PlaceOrder :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
      </v-main>
    </v-app>
  </div>
</template>

<script setup>
import BidAskDistribution from '@charts/BidAskDistribution.vue'
import PriceHistory from '@charts/PriceHistory.vue'
import PlaceOrder from '@trading/PlaceOrder.vue'
import OrderHistory from '@trading/OrderHistory.vue'
import ActiveOrders from '@trading/ActiveOrders.vue'
import MarketMessages from '@trading/MarketMessages.vue'
import { computed, watch, ref, nextTick, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useFormatNumber } from '@/composables/utils'
import { storeToRefs } from 'pinia'
import { useTraderStore } from '@/store/app'
import { useWebSocketStore } from '@/store/websocket'
import { debounce } from 'lodash'
import axios from '@/api/axios'
import NavigationService from '@/services/navigation'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Package,
  Banknote,
  Users,
  Clock,
  ArrowUp,
  ArrowDown,
  Search,
  History,
  Info,
  BarChart3,
  List,
  LineChart,
  Calculator,
} from 'lucide-vue-next'

const { formatNumber } = useFormatNumber()
const router = useRouter()
const store = useTraderStore()
const wsStore = useWebSocketStore()
const {
  goalMessage,
  initial_shares,
  pnl,
  vwap,
  remainingTime,
  isTradingStarted,
  currentHumanTraders,
  expectedHumanTraders,
  traderUuid,
  cash,
  sum_dinv,
  activeOrders,
  gameParams,
} = storeToRefs(store)

const formatDelta = computed(() => {
  if (sum_dinv.value == undefined) return ''
  const halfChange = Math.round(sum_dinv.value)
  return halfChange >= 0 ? '+' + halfChange : halfChange.toString()
})

// Debug reactive values for PnL display
const debugDisplayValues = computed(() => {
  const values = {
    pnl: pnl.value,
    initial_shares: initial_shares.value,
    cash: cash.value,
    sum_dinv: sum_dinv.value,
    formatDelta: formatDelta.value,
  }
  return values
})

const finalizingDay = () => {
  NavigationService.onTradingEnded()
}

watch(remainingTime, (newValue) => {
  if (newValue !== null && newValue <= 0 && isTradingStarted.value) {
    finalizingDay()
  }
})

// Remove the calculateZoom function and replace with a fixed value
const zoomLevel = ref(0.95) // Fixed 90% zoom

onMounted(async () => {
  // Apply zoom - use CSS zoom (not transform) to preserve position:fixed on the app bar
  document.body.style.zoom = '0.95'

  // Set default user role
  userRole.value = 'trader'

  // Start market timeout countdown if not started
  if (!isTradingStarted.value) {
    marketTimeoutInterval.value = setInterval(() => {
      if (marketTimeRemaining.value > 0) {
        marketTimeRemaining.value--
      }
    }, 1000)
  }
})

onUnmounted(() => {
  // Remove other cleanup code if needed
})

// First, define the basic computed properties
// Don't default to 0 - let it be undefined until data loads
const goal = computed(() => store.traderAttributes?.goal)
const goalProgress = computed(() => store.traderAttributes?.goal_progress || 0)
const hasGoal = computed(() => goal.value !== undefined && goal.value !== 0)
const goalLoaded = computed(() => goal.value !== undefined)

// Then define the dependent computed properties
const isGoalAchieved = computed(() => {
  if (!hasGoal.value) return false
  return Math.abs(goalProgress.value) >= Math.abs(goal.value)
})

const goalType = computed(() => {
  if (!hasGoal.value) return 'free'
  return goal.value > 0 ? 'buy' : 'sell'
})

const goalProgressPercentage = computed(() => {
  if (!hasGoal.value) return 0
  const targetGoal = Math.abs(goal.value)
  const currentProgress = Math.abs(goalProgress.value)
  return Math.min((currentProgress / targetGoal) * 100, 100)
})

const goalProgressColor = computed(() => {
  if (isGoalAchieved.value) return 'light-green accent-4'
  return goal.value > 0 ? 'blue lighten-1' : 'red lighten-1'
})

const getGoalMessageClass = computed(() => {
  if (isGoalAchieved.value) return 'success-bg'
  return goal.value > 0 ? 'buy-bg' : 'sell-bg'
})

const getGoalMessageIcon = computed(() => {
  if (!hasGoal.value) return 'mdi-information'
  return goal.value > 0 ? 'mdi-arrow-up-bold' : 'mdi-arrow-down-bold'
})

const displayGoalMessage = computed(() => {
  if (!goalMessage.value) {
    return {
      type: 'info',
      text: 'You can freely trade. Your goal is to profit from the market.',
    }
  }
  return goalMessage.value
})

// Add this function to cancel all active orders
const cancelAllActiveOrders = () => {
  activeOrders.value.forEach((order) => {
    store.cancelOrder(order.id)
  })
}

// Watch for changes in isGoalAchieved
watch(isGoalAchieved, (newValue) => {
  if (newValue) {
    cancelAllActiveOrders()
  }
})

// Add function for role icons
const getRoleIcon = () => {
  if (!hasGoal.value) return Search
  return goal.value > 0 ? TrendingUp : TrendingDown
}

// Add function for goal icons
const getGoalIcon = () => {
  if (!hasGoal.value) return Search
  return goal.value > 0 ? ArrowUp : ArrowDown
}

// Add these to your existing refs/computed
const userRole = ref('')
const marketTimeRemaining = ref(null) // Infinite timeout
const marketTimeoutInterval = ref(null)

// Add these computed properties
const roleDisplay = computed(() => {
  // Don't show anything until goal data is loaded
  if (!goalLoaded.value) {
    return {
      text: 'Loading...',
      icon: 'mdi-loading',
      color: 'grey',
    }
  }
  
  // If goal is 0, user is a SPECULATOR
  if (!hasGoal.value) {
    return {
      text: 'SPECULATOR',
      icon: 'mdi-account-search',
      color: 'teal',
    }
  }
  
  // Informed trader with different types
  if (goal.value > 0) {
    return {
      text: 'INFORMED (BUY)',
      icon: 'mdi-trending-up',
      color: 'indigo',
    }
  }
  return {
    text: 'INFORMED (SELL)',
    icon: 'mdi-trending-down',
    color: 'deep-purple',
  }
})

// Replace the existing roleColor and roleIcon computed properties
const roleColor = computed(() => roleDisplay.value.color)
const roleIcon = computed(() => roleDisplay.value.icon)

// Add watcher for trading started
watch(isTradingStarted, (newValue) => {
  if (newValue && marketTimeoutInterval.value) {
    clearInterval(marketTimeoutInterval.value)
    marketTimeRemaining.value = 0
  }
})

// Add handler for market timeout
watch(marketTimeRemaining, (newValue) => {
  if (newValue === 0 && !isTradingStarted.value) {
    router.push({
      name: 'auth',
      query: { error: 'Market timed out - not enough traders joined' },
    })
  }
})

const goalTypeText = computed(() => {
  if (!hasGoal.value) return 'FREE'
  return goal.value > 0 ? 'BUY' : 'SELL'
})

const progressBarColor = computed(() => {
  if (goalProgressPercentage.value === 100) {
    return 'light-green accent-3'
  }
  if (goalProgressPercentage.value > 75) {
    return 'light-green lighten-1'
  }
  if (goalProgressPercentage.value > 50) {
    return 'amber lighten-1'
  }
  if (goalProgressPercentage.value > 25) {
    return 'orange lighten-1'
  }
  return 'deep-orange lighten-1'
})

// Add this computed property
const allTradersReady = computed(() => {
  // This should be updated based on the WebSocket status updates
  // You'll need to track this in your store
  return store.allTradersReady
})

// Add this computed property
const readyCount = computed(() => {
  return store.readyCount || 0
})

// Add a computed property to track trader count changes
const traderCountDisplay = computed(() => {
  return `${currentHumanTraders.value} / ${expectedHumanTraders.value}`
})

// Add a watcher to log changes (for debugging)
watch(
  [currentHumanTraders, expectedHumanTraders],
  ([newCurrent, newExpected], [oldCurrent, oldExpected]) => {
    // Trader count updated
  }
)

// Add to your existing imports
//import { ref } from 'vue';

// Add these refs
const showErrorAlert = ref(false)

// Add this method
const refreshPage = () => {
  window.location.reload()
}

// Modify your store watch or WebSocket handler to include error handling
watch(
  () => wsStore.ws,
  (newWs) => {
    if (newWs) {
      const debouncedHandler = debounce((event) => {
        try {
          if (
            typeof event.data === 'string' &&
            (event.data.startsWith('<!DOCTYPE') || event.data.startsWith('<html'))
          ) {
            showErrorAlert.value = true
            return
          }
          const data = JSON.parse(event.data)
          // Your normal message handling...
        } catch (error) {
          if (error.message.includes("Unexpected token '<'")) {
            showErrorAlert.value = true
          }
          // WebSocket message error
        }
      }, 16) // Debounce to roughly one frame (60fps)

      newWs.addEventListener('message', debouncedHandler)
    }
  },
  { immediate: true }
)

// Add this computed property
const isInitialized = computed(() => {
  return Boolean(traderUuid.value && store.traderAttributes)
})

// Dynamic header height adjustment
onMounted(() => {
  const adjustMainContent = () => {
    const header = document.querySelector('.dynamic-header')
    const vApp = document.querySelector('.v-application')
    if (header && vApp) {
      const headerHeight = header.offsetHeight
      vApp.style.setProperty('--v-layout-top', `${headerHeight}px`)
      const main = document.querySelector('.v-main')
      if (main) {
        main.style.paddingTop = `${headerHeight}px`
      }
    }
  }
  
  // Use nextTick to ensure DOM is ready
  nextTick(() => {
    adjustMainContent()
    // Also adjust after a short delay to catch any layout changes
    setTimeout(adjustMainContent, 100)
  })
  
  window.addEventListener('resize', adjustMainContent)
  
  onUnmounted(() => {
    window.removeEventListener('resize', adjustMainContent)
  })
})
</script>

<style scoped>
.trading-dashboard {
  font-family: 'Inter', sans-serif;
  font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
}

.dashboard-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: -0.025em;
}

.title-icon {
  color: #3b82f6;
}

.v-card {
  border-radius: 16px;
  box-shadow:
    0 1px 3px 0 rgba(0, 0, 0, 0.1),
    0 1px 2px 0 rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.tool-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: -0.025em;
}

.tool-icon {
  color: #6366f1;
}

.tool-card {
  display: flex;
  flex-direction: column;
  background-color: white;
  transition: all 0.2s ease;
}

.tool-card:hover {
  transform: translateY(-1px);
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.price-history-card {
  /* Remove flex-grow to prevent blank space below chart */
}

/* Dashboard stats responsive layout */
.dashboard-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

/* Modern chip styles */
.stats-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(248, 250, 252, 0.8);
  border: 1px solid rgba(203, 213, 225, 0.5);
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.stat-chip:hover {
  background: rgba(241, 245, 249, 0.9);
  border-color: rgba(203, 213, 225, 0.8);
}

.chip-icon {
  color: #6b7280;
}

.chip-label {
  font-weight: 500;
  color: #6b7280;
}

.chip-value {
  font-weight: 600;
  color: #111827;
}

.role-chip-modern {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
  margin-right: 16px;
  letter-spacing: 0.025em;
}

.role-chip-modern.teal {
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
}

.role-chip-modern.indigo {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
}

.role-chip-modern.deep-purple {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
}

.role-chip-modern.grey {
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
  opacity: 0.8;
}

.time-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 20px;
  color: white;
  font-weight: 600;
  font-size: 0.875rem;
  letter-spacing: 0.025em;
}

/* Goal chip styles */
.goal-chip-modern {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-radius: 20px;
  color: white;
  font-weight: 600;
  font-size: 0.875rem;
  margin-right: 12px;
  min-width: 180px;
}

.goal-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.goal-icon {
  color: white;
}

.goal-type-text {
  font-weight: 700;
  letter-spacing: 0.05em;
  font-size: 0.75rem;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.progress-bar-modern {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill-modern {
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 6px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 35px;
  text-align: right;
}

/* Goal background colors */
.success-bg {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
}

.buy-bg {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

.sell-bg {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

/* Dynamic header styles */
.dynamic-header {
  min-height: 64px !important;
  height: auto !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 1000 !important;
}

.dynamic-header .v-toolbar__content {
  height: auto !important;
  padding: 8px 0 !important;
}

/* Dynamic main content adjustment */
.dynamic-main {
  padding-top: 64px !important;
  transition: padding-top 0.2s ease;
}

.v-application .v-main {
  padding-top: 64px !important;
  transition: padding-top 0.2s ease;
}

/* Alert styles */
.v-alert {
  max-width: 500px;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  font-weight: 500;
}
</style>
