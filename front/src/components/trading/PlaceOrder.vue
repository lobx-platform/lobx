<template>
  <div class="trading-panel">
    <!-- Show pause notification -->
    <div v-if="isHumanTraderPaused" class="pause-banner">
      TRADING PAUSED
    </div>
    <div class="orders-container">
      <div class="order-column">
        <div class="column-header buy-header">Buy Orders</div>
        <div v-if="buyPrices.length === 0" class="no-orders">
          No Buy Orders
          <div v-if="bestAsk !== null">Best Ask: {{ formatPrice(bestAsk) }}</div>
        </div>
        <div
          v-for="(price, index) in buyPrices"
          :key="'buy-' + index"
          class="order-row bid-row"
          :class="{
            'best-price': price === bestAsk,
            'locked': !canBuy,
            'paused': isHumanTraderPaused,
          }"
        >
          <span class="price-value">{{ formatPrice(price) }}</span>
          <button
            class="order-btn buy-btn"
            @click="sendOrder('BUY', price)"
            :disabled="isBuyButtonDisabled(price) || isGoalAchieved || !canBuy || isHumanTraderPaused"
          >
            Buy
          </button>
        </div>
      </div>

      <div class="order-column">
        <div class="column-header sell-header">Sell Orders</div>
        <div v-if="sellPrices.length === 0" class="no-orders">
          No Sell Orders
          <div v-if="bestBid !== null">Best Bid: {{ formatPrice(bestBid) }}</div>
        </div>
        <div
          v-for="(price, index) in sellPrices"
          :key="'sell-' + index"
          class="order-row ask-row"
          :class="{
            'best-price': price === bestBid,
            'locked': !canSell,
            'paused': isHumanTraderPaused,
          }"
        >
          <span class="price-value">{{ formatPrice(price) }}</span>
          <button
            class="order-btn sell-btn"
            @click="sendOrder('SELL', price)"
            :disabled="isSellButtonDisabled() || isGoalAchieved || !canSell || isHumanTraderPaused"
          >
            Sell
          </button>
        </div>
      </div>
    </div>
  </div>
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
      { length: 6 },
      (_, i) => bestBid.value + step.value * 1 - step.value * i
    )
  } else {
    return Array.from(
      { length: 6},
      (_, i) => bestAsk.value - step.value * i)
  }
})

const sellPrices = computed(() => {
  if (bestBid.value === null || !orderBookLevels.value) {
    return Array.from(
      { length: 6 },
      (_, i) => bestAsk.value - step.value * 1 + step.value * i
    )
  } else {
    return Array.from(
      { length: 6},
      (_, i) => bestBid.value + step.value * i)
  }
})

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

  if (humanTraderParam) {
    return humanTraderParam.value === 'paused'
  }

  if (!isPausingSystemActive.value) {
    return false
  }

  if (noiseTraderParam) {
    const isNoiseSleeping = noiseTraderParam.value === 'sleeping'
    return !isNoiseSleeping
  }

  return false
})

// Check if pausing system is active
const isPausingSystemActive = computed(() => {
  const noiseTraderParam = extraParams.value.find(param => param.var_name === 'noise_trader_status')
  const humanTraderParam = extraParams.value.find(param => param.var_name === 'human_trader_status')
  return (noiseTraderParam && noiseTraderParam.value !== null) ||
         (humanTraderParam && humanTraderParam.value !== null)
})

function sendOrder(orderType, price) {
  if (
    !props.isGoalAchieved &&
    !isHumanTraderPaused.value &&
    ((orderType === 'BUY' && canBuy.value) || (orderType === 'SELL' && canSell.value))
  ) {
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

function formatPrice(price) {
  return Math.round(price).toString()
}

function checkMobile() {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  )
}

// Check if a price is the AI suggested price
function isSuggestedPrice(price, side) {
  return false
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
  font-family: var(--font-family);
  background: var(--color-bg-surface);
}

.pause-banner {
  background: var(--color-error-light);
  border-bottom: 1px solid var(--color-ask-border);
  color: var(--color-error);
  font-family: var(--font-mono);
  font-weight: var(--font-bold);
  font-size: var(--text-xs);
  padding: 4px 8px;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.orders-container {
  display: flex;
  gap: 8px;
  padding: 8px;
}

.order-column {
  flex: 1;
}

.column-header {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  padding: 0 0 4px 0;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--color-border);
}

.buy-header {
  border-bottom-color: var(--color-bid-border);
}

.sell-header {
  border-bottom-color: var(--color-ask-border);
}

.no-orders {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  padding: 8px 0;
}

.order-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 6px;
  margin-bottom: 2px;
  border-radius: var(--radius-sm);
}

.bid-row {
  border-left: 2px solid var(--color-bid);
}

.ask-row {
  border-left: 2px solid var(--color-ask);
}

.price-value {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.order-btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  padding: 3px 10px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: #fff;
}

.buy-btn {
  background: var(--color-bid);
}

.buy-btn:disabled {
  background: var(--color-border);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.sell-btn {
  background: var(--color-ask);
}

.sell-btn:disabled {
  background: var(--color-border);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.best-price .price-value {
  color: var(--color-primary);
}

/* add AGG next to the top of book prices */
.best-price .price-value::after {
  content: " AGG";
  font-size: 0.75em;
  margin-left: 4px;
}

  
.locked {
  opacity: 0.35;
}

.paused {
  opacity: 0.2;
  pointer-events: none;
}
</style>
