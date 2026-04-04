<script setup>
import { computed } from 'vue'
import { useTraderStore } from '@/store/app'
import { useMarketStore } from '@/store/market'
import { storeToRefs } from 'pinia'

const traderStore = useTraderStore()
const marketStore = useMarketStore()
const { executedOrders, traderUuid } = storeToRefs(traderStore)
const { recentTransactions } = storeToRefs(marketStore)

const filledOrders = computed(() => {
  // Only use transactions from market store to avoid double counting
  // The backend handles inventory updates, so we don't need to mix with executedOrders
  const relevantTransactions = recentTransactions.value.filter((t) => {
    const isBidTrader = t.bid_trader_id === traderUuid.value
    const isAskTrader = t.ask_trader_id === traderUuid.value
    return isBidTrader || isAskTrader
  })

  return relevantTransactions
})

const groupedOrders = computed(() => {
  const bids = {}
  const asks = {}

  filledOrders.value.forEach((order) => {
    // Determine if this is a bid or ask for the current trader
    const isBid =
      order.bid_trader_id === traderUuid.value ||
      (order.trader_id === traderUuid.value &&
        ['BUY', 'BID', 1].includes(order.type || order.order_type))

    const isAsk =
      order.ask_trader_id === traderUuid.value ||
      (order.trader_id === traderUuid.value &&
        ['SELL', 'ASK', -1].includes(order.type || order.order_type))

    // Skip if not the current trader's order
    if (!isBid && !isAsk) return

    const group = isBid ? bids : asks
    const price = order.price || order.transaction_price
    // Use transaction_amount for transactions, amount for regular orders, default to 1
    const amount = order.transaction_amount || order.amount || 1
    const timestamp = new Date(order.timestamp || order.transaction_time).getTime()

    if (!group[price]) {
      group[price] = {
        price,
        amount,
        latestTime: timestamp,
      }
    } else {
      group[price].amount += amount
      if (timestamp > group[price].latestTime) {
        group[price].latestTime = timestamp
      }
    }
  })

  const sortByTimeDesc = (a, b) => b.latestTime - a.latestTime

  return {
    bids: Object.values(bids).sort(sortByTimeDesc),
    asks: Object.values(asks).sort(sortByTimeDesc),
  }
})

const tradingSummary = computed(() => {
  let buyCount = 0
  let sellCount = 0
  let buyVolume = 0
  let sellVolume = 0
  let buyValue = 0
  let sellValue = 0

  filledOrders.value.forEach((order) => {
    const isBid =
      order.bid_trader_id === traderUuid.value ||
      (order.trader_id === traderUuid.value &&
        ['BUY', 'BID', 1].includes(order.type || order.order_type))

    const price = order.price || order.transaction_price
    // Use transaction_amount for transactions, amount for regular orders, default to 1
    const amount = order.transaction_amount || order.amount || 1

    if (isBid) {
      buyCount++
      buyVolume += amount
      buyValue += price * amount
    } else {
      sellCount++
      sellVolume += amount
      sellValue += price * amount
    }
  })

  return {
    buyCount,
    sellCount,
    buyVWAP: buyVolume > 0 ? (buyValue / buyVolume).toFixed(2) : 0,
    sellVWAP: sellVolume > 0 ? (sellValue / sellVolume).toFixed(2) : 0,
  }
})

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}
</script>

<template>
  <v-card height="100%" elevation="3" class="order-history-card">
    <div class="trading-summary pa-2">
      <div class="vwap-display">
        <div class="label">Average Price</div>
        <span class="vwap-item buy"> Buy: {{ tradingSummary.buyVWAP }}</span>
        <span class="vwap-divider">|</span>
        <span class="vwap-item sell"> Sell: {{ tradingSummary.sellVWAP }}</span>
      </div>
      <!-- <div class="count-display">
        <div class="label">Count</div>
        <span class="count-item buy">{{ tradingSummary.buyCount }}</span>
        <span class="count-divider">|</span>
        <span class="count-item sell">{{ tradingSummary.sellCount }}</span>
      </div> -->
    </div>

    <v-divider></v-divider>

    <div class="order-history-container px-4">
      <div v-if="groupedOrders.bids.length || groupedOrders.asks.length" class="order-columns">
        <div class="order-column">
          <TransitionGroup name="order-change">
            <div
              v-for="order in groupedOrders.bids"
              :key="order.price"
              class="order-item bid elevation-1"
            >
              <div class="price-amount">
                <span class="price">{{ Math.round(order.price) }}</span>
                <span class="amount">{{ order.amount }} shares</span>
              </div>
              <div class="time">
                <v-icon size="12" class="mr-1">mdi-clock-outline</v-icon>
                {{ formatTime(order.latestTime) }}
              </div>
            </div>
          </TransitionGroup>
        </div>
        <div class="order-column">
          <TransitionGroup name="order-change">
            <div
              v-for="order in groupedOrders.asks"
              :key="order.price"
              class="order-item ask elevation-1"
            >
              <div class="price-amount">
                <span class="price">{{ Math.round(order.price) }}</span>
                <span class="amount">{{ order.amount }} shares</span>
              </div>
              <div class="time">
                <v-icon size="12" class="mr-1">mdi-clock-outline</v-icon>
                {{ formatTime(order.latestTime) }}
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>
      <div v-else class="no-orders-message">
        <v-icon color="grey" size="40" class="mb-2">mdi-clipboard-text-outline</v-icon>
        <div>No executed trades yet</div>
      </div>
    </div>
  </v-card>
</template>

<style scoped>
.order-history-card {
  background: var(--color-bg-surface);
  font-family: var(--font-family);
}

.trading-summary {
  background: var(--color-bg-elevated);
  padding: 6px var(--space-3);
}

.vwap-display,
.count-display {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  font-size: var(--text-sm);
  white-space: nowrap;
  position: relative;
}

.label {
  position: absolute;
  left: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.vwap-item,
.count-item {
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
}

.vwap-item.buy,
.count-item.buy {
  color: var(--color-bid);
}

.vwap-item.sell,
.count-item.sell {
  color: var(--color-ask);
}

.order-history-container {
  height: 200px;
  overflow-y: auto;
}

.order-columns {
  display: flex;
  gap: var(--space-2);
}

.order-column {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.order-item {
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  padding: 3px 8px;
  margin-bottom: 3px;
  font-size: var(--text-sm);
  display: flex;
  flex-direction: column;
  transition: border-color var(--transition-fast);
  border: var(--border-width) solid transparent;
}

.order-item:hover {
  border-color: var(--color-border-strong);
}

.order-item.bid {
  border-left: 2px solid var(--color-bid);
  background: var(--color-bid-bg);
}

.order-item.ask {
  border-left: 2px solid var(--color-ask);
  background: var(--color-ask-bg);
}

.price-amount {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1px;
}

.price {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.amount {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
}

.time {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.no-orders-message {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.order-change-enter-active,
.order-change-leave-active {
  transition: all 0.3s ease;
}

.order-change-enter-from,
.order-change-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

/* Scrollbar */
.order-history-container::-webkit-scrollbar {
  width: 4px;
}

.order-history-container::-webkit-scrollbar-track {
  background: transparent;
}

.order-history-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}

.order-history-container::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>
