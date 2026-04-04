<template>
  <v-card height="100%" elevation="3" class="trading-panel">
    <!-- Show pause notification overlapping headers -->
    <div v-if="isHumanTraderPaused" class="pause-overlay">
      <div class="pause-banner">
        <v-icon color="orange" small class="mr-1">mdi-pause</v-icon>
        Trading PAUSED - Buttons disabled
      </div>
    </div>
    <div class="orders-container">
      <div class="order-column buy-column">
        <h3 class="order-type-title">
          <v-icon left color="primary">mdi-arrow-up-bold</v-icon>
          Buy Orders
        </h3>
        <div v-if="buyPrices.length === 0">
          No Buy Orders
          <div v-if="bestAsk !== null">Best Ask Price: {{ formatPrice(bestAsk) }}</div>
        </div>
        <div
          v-for="(price, index) in buyPrices"
          :key="'buy-' + index"
          class="order-item bid"
          :class="{ 
            'best-price': price === bestAsk, 
            'locked': !canBuy,
            'paused': isHumanTraderPaused,
            'ai-suggested': isSuggestedPrice(price, 'BUY')
          }"
        >
          <div class="order-content">
            <span class="order-type">BUY</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestAsk" color="primary" small>mdi-star</v-icon>
          </div>
          <v-btn
            @click="sendOrder('BUY', price)"
            :disabled="isBuyButtonDisabled(price) || isGoalAchieved || !canBuy || isHumanTraderPaused"
            :color="isHumanTraderPaused || isBuyButtonDisabled(price) ? 'grey' : 'primary'"
            small
          >
            Buy
          </v-btn>
        </div>
      </div>

      <div class="order-column sell-column">
        <h3 class="order-type-title">
          <v-icon left color="error">mdi-arrow-down-bold</v-icon>
          Sell Orders
        </h3>
        <div v-if="sellPrices.length === 0">
          No Sell Orders
          <div v-if="bestBid !== null">Best Bid Price: {{ formatPrice(bestBid) }}</div>
        </div>
        <div
          v-for="(price, index) in sellPrices"
          :key="'sell-' + index"
          class="order-item ask"
          :class="{ 
            'best-price': price === bestBid, 
            'locked': !canSell,
            'paused': isHumanTraderPaused,
            'ai-suggested': isSuggestedPrice(price, 'SELL')
          }"
        >
          <div class="order-content">
            <span class="order-type">SELL</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestBid" color="error" small>mdi-star</v-icon>
          </div>
          <v-btn
            @click="sendOrder('SELL', price)"
            :disabled="isSellButtonDisabled() || isGoalAchieved || !canSell || isHumanTraderPaused"
            :color="isHumanTraderPaused || isSellButtonDisabled() ? 'grey' : 'error'"
            small
          >
            Sell
          </v-btn>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useTraderStore } from '@/store/app'
import { useMarketStore } from '@/store/market'
import { useUIStore } from '@/store/ui'
import { storeToRefs } from 'pinia'

const props = defineProps({
  isGoalAchieved: {
    type: Boolean,
    default: false,
  },
  goalType: {
    type: String,
    default: 'free',
  },
})

const tradingStore = useTraderStore()
const marketStore = useMarketStore()
const uiStore = useUIStore()
const { gameParams, trader } = storeToRefs(tradingStore)
const { bidData, askData, extraParams } = storeToRefs(marketStore)

const step = computed(() => gameParams.value.step || 1)
const hasAskData = computed(() => askData.value.length > 0)
const hasBidData = computed(() => bidData.value.length > 0)
const bestBid = computed(() =>
  hasBidData.value ? Math.max(...bidData.value.map((bid) => bid.x)) : null
)
const bestAsk = computed(() =>
  hasAskData.value ? Math.min(...askData.value.map((ask) => ask.x)) : null
)

const orderBookLevels = computed(() => gameParams.value.order_book_levels || 5)

const buyPrices = computed(() => {
  if (bestAsk.value === null || !orderBookLevels.value) {
    return Array.from(
      //{ length: orderBookLevels.value },
      { length: 6 }, // replace 6 with orderBookLevels.value
      (_, i) => bestBid.value + step.value * 1 - step.value * i
    )
  } else {
    return Array.from(
      { length: 6},  // replace 6 with orderBookLevels.value
      (_, i) => bestAsk.value - step.value * i)
  }
})

// const buyPrices = computed(() => {
//   if (bestAsk.value === null || !orderBookLevels.value) return [];
//   return Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value * i);
// });

// const sellPrices = computed(() => {
//   if (bestBid.value === null || !orderBookLevels.value) return [];
//   return Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value * i);
// });

const sellPrices = computed(() => {
  if (bestBid.value === null || !orderBookLevels.value) {
    return Array.from(
      //{ length: orderBookLevels.value },
      { length: 6 }, // replace 6 with orderBookLevels.value
      (_, i) => bestAsk.value - step.value * 1 + step.value * i
    )
  } else {
    return Array.from(
      { length: 6}, // replace 6 with orderBookLevels.value
      (_, i) => bestBid.value + step.value * i)
  }
})

// const isBuyButtonDisabled = computed(() => !hasAskData.value);
const canAffordBuy = (price) => {
  return tradingStore.availableCash >= price
}

const canAffordSell = () => {
  return tradingStore.availableShares >= 1
}

const isBuyButtonDisabled = (price) => {
  return !canAffordBuy(price)
}

const isSellButtonDisabled = () => {
  return !canAffordSell()
}

const isMobile = ref(false)

const canBuy = computed(() => props.goalType === 'buy' || props.goalType === 'free')
const canSell = computed(() => props.goalType === 'sell' || props.goalType === 'free')

// Check if noise trader is sleeping
const isNoiseTraderSleeping = computed(() => {
  const noiseTraderParam = extraParams.value.find(param => param.var_name === 'noise_trader_status')
  return noiseTraderParam?.value === 'sleeping'
})

// Check if human trader is paused (when algos are active)
const isHumanTraderPaused = computed(() => {
  const humanTraderParam = extraParams.value.find(param => param.var_name === 'human_trader_status')
  const noiseTraderParam = extraParams.value.find(param => param.var_name === 'noise_trader_status')
  
  // If human trader status exists, use it
  if (humanTraderParam) {
    return humanTraderParam.value === 'paused'
  }
  
  // If no pausing system is active (no status updates from backend), humans should be active
  if (!isPausingSystemActive.value) {
    return false
  }
  
  // Fallback: if noise trader is active (not sleeping), human should be paused
  if (noiseTraderParam) {
    const isNoiseSleeping = noiseTraderParam.value === 'sleeping'
    return !isNoiseSleeping
  }
  
  return false
})

// Check if pausing system is active (backend is sending status updates)
const isPausingSystemActive = computed(() => {
  const noiseTraderParam = extraParams.value.find(param => param.var_name === 'noise_trader_status')
  const humanTraderParam = extraParams.value.find(param => param.var_name === 'human_trader_status')
  // Only consider pausing active if we've received actual status updates from backend
  // (i.e., values are not null and not the default)
  return (noiseTraderParam && noiseTraderParam.value !== null) || 
         (humanTraderParam && humanTraderParam.value !== null)
})

function sendOrder(orderType, price) {
  if (
    !props.isGoalAchieved &&
    !isHumanTraderPaused.value &&
    ((orderType === 'BUY' && canBuy.value) || (orderType === 'SELL' && canSell.value))
  ) {
    // check if trader has sufficient balance (considering locked balances in active orders)
    if (orderType === 'BUY') {
      if (tradingStore.availableCash < price) {
        uiStore.showMessage('insufficient cash to buy')
        return
      }
    } else if (orderType === 'SELL') {
      if (tradingStore.availableShares < 1) {
        uiStore.showMessage('insufficient shares to sell')
        return
      }
    }

    const newOrder = {
      id: Date.now().toString(),
      order_type: orderType,
      price: price,
      amount: 1,
      status: 'pending',
    }
    tradingStore.addOrder(newOrder)
  }
}

function getButtonColor(price, orderType) {
  if (orderType === 'buy') {
    return price === bestAsk.value ? 'primary' : 'grey lighten-3'
  } else if (orderType === 'sell') {
    return price === bestBid.value ? 'error' : 'grey lighten-3'
  }
}

function formatPrice(price) {
  return Math.round(price).toString()
}

function checkMobile() {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  )
}

// Check if a price is the AI suggested price (uses same clamping logic as AIAdvisor)
function isSuggestedPrice(price, side) {
  // AI advisor removed - never highlight
  return false
  
  // Determine expected side based on goal
  const goal = tradingStore.traderAttributes?.goal || 0
  const expectedSide = goal > 0 ? 'BUY' : 'SELL'
  
  if (expectedSide !== side) return false
  
  // Use the same price arrays as this component
  const availablePrices = goal > 0 ? buyPrices.value : sellPrices.value
  
  if (availablePrices.length === 0) return advicePrice === price
  
  // Find the closest available price (same logic as AIAdvisor)
  let closest = availablePrices[0]
  let minDiff = Math.abs(advicePrice - closest)
  
  for (const p of availablePrices) {
    const diff = Math.abs(advicePrice - p)
    if (diff < minDiff) {
      minDiff = diff
      closest = p
    }
  }
  
  return closest === price
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.trading-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-surface);
  font-family: var(--font-family);
}

.pause-overlay {
  position: absolute;
  top: 6px;
  left: 6px;
  right: 6px;
  z-index: 1000;
  pointer-events: none;
}

.pause-banner {
  background: var(--color-error-light);
  border: var(--border-width) solid rgba(239, 68, 68, 0.4);
  color: var(--color-error);
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  font-size: var(--text-xs);
  padding: 6px 10px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
  pointer-events: auto;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.orders-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: var(--space-3);
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
}

.order-column {
  flex: 0 0 48%;
}

.order-type-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-2);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.order-item {
  font-size: var(--text-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-1-5);
  padding: var(--space-1-5) var(--space-2);
  border-radius: var(--radius-md);
  border: var(--border-width) solid transparent;
  transition: all var(--transition-fast);
}

.order-item.bid {
  background: var(--color-bid-bg);
  border-color: var(--color-bid-border);
}

.order-item.ask {
  background: var(--color-ask-bg);
  border-color: var(--color-ask-border);
}

.order-item:hover {
  border-color: var(--color-border-strong);
}

.order-type {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  letter-spacing: var(--tracking-wider);
  color: var(--color-text-muted);
}

.price {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.order-content {
  display: flex;
  align-items: center;
}

.order-content > * {
  margin-right: 6px;
}

.best-price {
  font-weight: bold;
}

.best-price .price {
  color: var(--color-primary);
}

.locked {
  opacity: 0.35;
}

.paused {
  opacity: 0.2;
  background: var(--color-bg-elevated) !important;
  border: var(--border-width) dashed var(--color-border-strong);
  pointer-events: none;
}

.ai-suggested {
  border: var(--border-width) solid var(--color-primary) !important;
  box-shadow: var(--shadow-glow-sm);
}

.sleep-notification-overlay {
  position: absolute;
  top: -6px;
  left: 6px;
  right: 6px;
  z-index: 1000;
  pointer-events: none;
}

.sleep-notification {
  background: var(--color-warning-light);
  border: var(--border-width) solid rgba(245, 158, 11, 0.3);
  color: var(--color-warning);
  padding: 6px 10px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  pointer-events: auto;
}

.sleep-notification.active {
  background: var(--color-success-light);
  border-color: rgba(34, 197, 94, 0.3);
  color: var(--color-success);
}

.sleep-notification.paused {
  background: var(--color-error-light);
  border: var(--border-width) solid rgba(239, 68, 68, 0.4);
  color: var(--color-error);
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  font-size: var(--text-xs);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
  z-index: 1001;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}
</style>
