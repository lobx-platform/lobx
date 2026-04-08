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
    const isBid =
      order.bid_trader_id === traderUuid.value ||
      (order.trader_id === traderUuid.value &&
        ['BUY', 'BID', 1].includes(order.type || order.order_type))

    const isAsk =
      order.ask_trader_id === traderUuid.value ||
      (order.trader_id === traderUuid.value &&
        ['SELL', 'ASK', -1].includes(order.type || order.order_type))

    if (!isBid && !isAsk) return

    const group = isBid ? bids : asks
    const price = order.price || order.transaction_price
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
  <div class="order-history">
    <div class="vwap-row">
      <span class="vwap-label">Avg Price</span>
      <span class="vwap-value bid-color">Buy: {{ tradingSummary.buyVWAP }}</span>
      <span class="vwap-sep">|</span>
      <span class="vwap-value ask-color">Sell: {{ tradingSummary.sellVWAP }}</span>
    </div>

    <div class="divider"></div>

    <div class="orders-scroll">
      <div v-if="groupedOrders.bids.length || groupedOrders.asks.length" class="order-columns">
        <div class="order-col">
          <div
            v-for="order in groupedOrders.bids"
            :key="order.price"
            class="trade-row bid-row"
          >
            <div class="trade-main">
              <span class="trade-price">{{ Math.round(order.price) }}</span>
              <span class="trade-amount">{{ order.amount }}sh</span>
            </div>
            <div class="trade-time">{{ formatTime(order.latestTime) }}</div>
          </div>
        </div>
        <div class="order-col">
          <div
            v-for="order in groupedOrders.asks"
            :key="order.price"
            class="trade-row ask-row"
          >
            <div class="trade-main">
              <span class="trade-price">{{ Math.round(order.price) }}</span>
              <span class="trade-amount">{{ order.amount }}sh</span>
            </div>
            <div class="trade-time">{{ formatTime(order.latestTime) }}</div>
          </div>
        </div>
      </div>
      <div v-else class="no-trades">No executed trades yet</div>
    </div>
  </div>
</template>

<style scoped>
.order-history {
  font-family: var(--font-family);
  background: var(--color-bg-surface);
}

.vwap-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--color-bg-elevated);
  font-size: var(--text-sm);
}

.vwap-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  margin-right: auto;
}

.vwap-value {
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
}

.bid-color {
  color: var(--color-bid);
}

.ask-color {
  color: var(--color-ask);
}

.vwap-sep {
  color: var(--color-text-muted);
}

.divider {
  height: 1px;
  background: var(--color-border);
}

.orders-scroll {
  height: 200px;
  overflow-y: auto;
  padding: 8px;
}

.order-columns {
  display: flex;
  gap: 8px;
}

.order-col {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.trade-row {
  padding: 3px 8px;
  margin-bottom: 2px;
  border-radius: var(--radius-sm);
}

.bid-row {
  border-left: 2px solid var(--color-bid);
}

.ask-row {
  border-left: 2px solid var(--color-ask);
}

.trade-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trade-price {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.trade-amount {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.trade-time {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--color-text-muted);
  text-align: right;
}

.no-trades {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: 32px 16px;
}

/* Scrollbar */
.orders-scroll::-webkit-scrollbar {
  width: 4px;
}

.orders-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.orders-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}
</style>
