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

      <v-app-bar app elevation="0" height="auto" class="dynamic-header">
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

      <v-main class="dynamic-main">
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
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
// lodash debounce removed — no longer needed with Socket.IO
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
const sessionStore = useSessionStore()
const authStore = useAuthStore()
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

  // Always initialize trader on mount (subscribes to wsBus events + connects WS if needed)
  const traderId = store.traderUuid || sessionStore.traderId || authStore.traderId
  if (traderId) {
    try {
      await store.initializeTrader(traderId)
    } catch (e) {
      console.warn('Trader init on trading page:', e)
    }
  }

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

// Watch Socket.IO connection errors
watch(
  () => wsStore.isConnected,
  (connected) => {
    if (!connected && wsStore.socket) {
      // Socket.IO handles reconnection automatically
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
  font-family: var(--font-family);
  background: var(--color-bg-page);
}

/* ===== HEADER BAR ===== */
.dashboard-title {
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-bright);
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: var(--tracking-wide);
}

.title-icon {
  color: var(--color-primary);
}

/* ===== TOOL CARDS (panels) ===== */
.v-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: var(--border-width) solid var(--color-border);
  background: var(--color-bg-surface);
}

.tool-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
}

.tool-icon {
  color: var(--color-primary);
  opacity: 0.7;
}

.tool-card {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-surface);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.tool-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.price-history-card {
  /* No flex-grow */
}

/* ===== STATS BAR ===== */
.dashboard-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.stats-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  transition: border-color var(--transition-fast);
}

.stat-chip:hover {
  border-color: var(--color-border-strong);
}

.chip-icon {
  color: var(--color-text-muted);
  opacity: 0.6;
}

.chip-label {
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.chip-value {
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
  color: var(--color-text-bright);
  font-size: var(--text-sm);
}

/* ===== ROLE CHIP ===== */
.role-chip-modern {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-text-inverse);
  margin-right: 8px;
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
}

.role-chip-modern.teal {
  background: var(--color-primary);
}

.role-chip-modern.indigo {
  background: #2563EB;
}

.role-chip-modern.deep-purple {
  background: #7C3AED;
}

.role-chip-modern.grey {
  background: var(--color-text-muted);
  opacity: 0.7;
}

/* ===== TIME CHIP ===== */
.time-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  background: var(--color-primary-light);
  border: var(--border-width) solid var(--color-primary-muted);
  border-radius: var(--radius-md);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  font-size: var(--text-lg);
  letter-spacing: var(--tracking-wide);
}

/* ===== GOAL CHIP ===== */
.goal-chip-modern {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 12px;
  border-radius: var(--radius-md);
  color: white;
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  margin-right: 6px;
  min-width: 160px;
}

.goal-content {
  display: flex;
  align-items: center;
  gap: 4px;
}

.goal-icon {
  color: white;
  opacity: 0.9;
}

.goal-type-text {
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  letter-spacing: var(--tracking-wider);
  font-size: var(--text-xs);
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.progress-bar-modern {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill-modern {
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  min-width: 32px;
  text-align: right;
}

/* Goal background colors */
.success-bg {
  background: var(--color-bid);
}

.buy-bg {
  background: #2563EB;
}

.sell-bg {
  background: var(--color-ask);
}

/* ===== DYNAMIC HEADER ===== */
.dynamic-header {
  min-height: 52px !important;
  height: auto !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 1000 !important;
  background: var(--color-bg-surface) !important;
  border-bottom: var(--border-width) solid var(--color-border) !important;
  box-shadow: var(--shadow-xs) !important;
}

.dynamic-header .v-toolbar__content {
  height: auto !important;
  padding: 6px 0 !important;
}

.dynamic-main {
  padding-top: 52px !important;
  transition: padding-top 0.2s ease;
  background: var(--color-bg-page) !important;
}

.v-application .v-main {
  padding-top: 52px !important;
  transition: padding-top 0.2s ease;
  background: var(--color-bg-page) !important;
}

/* ===== ALERT ===== */
.v-alert {
  max-width: 500px;
  box-shadow: var(--shadow-md);
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
}
</style>
