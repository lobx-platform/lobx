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

      <header class="dashboard-header">
        <div class="header-inner">
          <h1 class="dashboard-title">LOBX</h1>
          <div class="dashboard-stats">
            <span class="role-label">{{ roleDisplay.text }}</span>
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-label">PnL</span>
                <span class="stat-value">{{ pnl }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Shares</span>
                <span class="stat-value">{{ initial_shares }} {{ formatDelta }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Cash</span>
                <span class="stat-value">{{ cash }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Traders</span>
                <span class="stat-value"
                  >{{ currentHumanTraders }} / {{ expectedHumanTraders }}</span
                >
              </div>
            </div>
            <div v-if="hasGoal" class="goal-row" :class="getGoalMessageClass">
              <span class="goal-type-text">{{ goalTypeText }}</span>
              <div class="progress-bar-track">
                <div
                  class="progress-bar-fill"
                  :style="{ width: `${goalProgressPercentage}%` }"
                ></div>
              </div>
              <span class="progress-text"
                >{{ Math.abs(goalProgress) }}/{{ Math.abs(goal) }}</span
              >
            </div>
            <div class="time-display">
              <vue-countdown
                v-if="remainingTime"
                :time="remainingTime * 1000"
                v-slot="{ minutes, seconds }"
              >
                {{ minutes }}:{{ seconds.toString().padStart(2, '0') }}
              </vue-countdown>
              <span v-else>--:--</span>
            </div>
          </div>
        </div>
      </header>

      <v-main class="dashboard-main">
        <v-container fluid class="pa-4">
          <v-row>
            <!-- 3x2 Grid Layout -->
            <v-col cols="12" md="4" class="d-flex flex-column">
              <div class="panel mb-4">
                <div class="panel-title">Your Trades</div>
                <div class="panel-body">
                  <OrderHistory :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </div>
              </div>
              <div class="panel mb-4">
                <div class="panel-title">Market Info</div>
                <div class="panel-body">
                  <MarketMessages :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </div>
              </div>
            </v-col>

            <v-col cols="12" md="4" class="d-flex flex-column">
              <div class="panel mb-4">
                <div class="panel-title">Buy-Sell Chart</div>
                <div class="panel-body">
                  <BidAskDistribution :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </div>
              </div>
              <div class="panel mb-4">
                <div class="panel-title">Passive Orders</div>
                <div class="panel-body">
                  <ActiveOrders :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </div>
              </div>
            </v-col>

            <v-col cols="12" md="4" class="d-flex flex-column">
              <div class="panel mb-4">
                <div class="panel-title">Market Trade Price History</div>
                <div class="panel-body">
                  <PriceHistory :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </div>
              </div>
              <div class="panel mb-4">
                <div class="panel-title">Trading Panel</div>
                <div class="panel-body">
                  <PlaceOrder :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </div>
              </div>
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
import { computed, watch, ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useTraderStore } from '@/store/app'
import { useWebSocketStore } from '@/store/websocket'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import axios from '@/api/axios'
import NavigationService from '@/services/navigation'

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

const finalizingDay = () => {
  NavigationService.onTradingEnded()
}

watch(remainingTime, (newValue) => {
  if (newValue !== null && newValue <= 0 && isTradingStarted.value) {
    finalizingDay()
  }
})

const zoomLevel = ref(0.95)

onMounted(async () => {
  userRole.value = 'trader'

  const traderId = store.traderUuid || sessionStore.traderId || authStore.traderId
  if (traderId) {
    store._subscribeToEvents?.()

    try {
      await store.initializeTrader(traderId)
    } catch (e) {
      console.warn('Trader init on trading page:', e)
    }
    const { joinMarket } = await import('@/socket')
    joinMarket(traderId)
  }

  if (!isTradingStarted.value) {
    marketTimeoutInterval.value = setInterval(() => {
      if (marketTimeRemaining.value > 0) {
        marketTimeRemaining.value--
      }
    }, 1000)
  }
})

onUnmounted(() => {
  // cleanup
})

const goal = computed(() => store.traderAttributes?.goal)
const goalProgress = computed(() => store.traderAttributes?.goal_progress || 0)
const hasGoal = computed(() => goal.value !== undefined && goal.value !== 0)
const goalLoaded = computed(() => goal.value !== undefined)

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

const getGoalMessageClass = computed(() => {
  if (isGoalAchieved.value) return 'goal-success'
  return goal.value > 0 ? 'goal-buy' : 'goal-sell'
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

const cancelAllActiveOrders = () => {
  activeOrders.value.forEach((order) => {
    store.cancelOrder(order.id)
  })
}

watch(isGoalAchieved, (newValue) => {
  if (newValue) {
    cancelAllActiveOrders()
  }
})

const userRole = ref('')
const marketTimeRemaining = ref(null)
const marketTimeoutInterval = ref(null)

const roleDisplay = computed(() => {
  if (!goalLoaded.value) {
    return { text: 'Loading...' }
  }
  if (!hasGoal.value) {
    return { text: 'SPECULATOR' }
  }
  if (goal.value > 0) {
    return { text: 'INFORMED (BUY)' }
  }
  return { text: 'INFORMED (SELL)' }
})

watch(isTradingStarted, (newValue) => {
  if (newValue && marketTimeoutInterval.value) {
    clearInterval(marketTimeoutInterval.value)
    marketTimeRemaining.value = 0
  }
})

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

const allTradersReady = computed(() => {
  return store.allTradersReady
})

const readyCount = computed(() => {
  return store.readyCount || 0
})

const traderCountDisplay = computed(() => {
  return `${currentHumanTraders.value} / ${expectedHumanTraders.value}`
})

watch(
  [currentHumanTraders, expectedHumanTraders],
  ([newCurrent, newExpected], [oldCurrent, oldExpected]) => {
    // Trader count updated
  },
)

const showErrorAlert = ref(false)

const refreshPage = () => {
  window.location.reload()
}

watch(
  () => wsStore.isConnected,
  (connected) => {
    if (!connected && wsStore.socket) {
      // Socket.IO handles reconnection automatically
    }
  },
  { immediate: true },
)

const isInitialized = computed(() => {
  return Boolean(traderUuid.value && store.traderAttributes)
})

onMounted(() => {
  const adjustMainContent = () => {
    const header = document.querySelector('.dashboard-header')
    const main = document.querySelector('.dashboard-main')
    if (header && main) {
      const headerHeight = header.offsetHeight
      main.style.paddingTop = `${headerHeight}px`
    }
  }

  nextTick(() => {
    adjustMainContent()
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

/* ===== HEADER ===== */
.dashboard-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--color-bg-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 6px 16px;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.dashboard-title {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  letter-spacing: var(--tracking-wide);
  margin: 0;
}

/* ===== STATS ===== */
.dashboard-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.role-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-text-secondary);
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
}

.stats-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

/* ===== GOAL ===== */
.goal-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: var(--radius-md);
}

.goal-row.goal-success {
  background: var(--color-bid-bg);
}

.goal-row.goal-buy {
  background: rgba(0, 102, 255, 0.08);
}

.goal-row.goal-sell {
  background: var(--color-ask-bg);
}

.goal-type-text {
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  letter-spacing: var(--tracking-wider);
  font-size: var(--text-xs);
  color: var(--color-text-primary);
}

.progress-bar-track {
  width: 60px;
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: var(--color-text-primary);
  border-radius: 2px;
  transition: width 0.2s ease;
}

.progress-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

/* ===== TIMER ===== */
.time-display {
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  font-size: var(--text-lg);
  color: var(--color-text-primary);
  letter-spacing: var(--tracking-wide);
}

/* ===== PANELS ===== */
.panel {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border);
}

.panel-body {
  flex: 1;
}

/* ===== MAIN ===== */
.dashboard-main {
  padding-top: 52px;
  background: var(--color-bg-page);
}

.v-application .v-main {
  background: var(--color-bg-page);
}

/* ===== ALERT ===== */
.v-alert {
  max-width: 500px;
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
}
</style>
