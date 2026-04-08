<template>
  <div class="active-orders">
    <div class="orders-body">
      <div v-if="Object.keys(sortedOrderLevels).length === 0" class="no-orders">
        No active orders
      </div>
      <div v-else class="orders-columns">
        <div class="orders-col">
          <div
            v-for="[price, level] in sortedOrderLevels.buy"
            :key="price"
            class="order-level bid-level"
          >
            <div class="level-header">
              <span class="level-type">BUY</span>
              <span class="level-price">{{ formatPrice(price) }}</span>
            </div>
            <div class="level-details">
              <span class="level-amount">{{ level.amount }}</span>
              <div class="level-actions">
                <button
                  class="action-btn add-btn"
                  @click="addOrder(level.type, price)"
                  :disabled="isGoalAchieved"
                >+</button>
                <button
                  class="action-btn cancel-btn"
                  @click="cancelOrder(level.type, price)"
                  :disabled="isGoalAchieved"
                >-</button>
              </div>
            </div>
          </div>
        </div>
        <div class="orders-col">
          <div
            v-for="[price, level] in sortedOrderLevels.sell"
            :key="price"
            class="order-level ask-level"
          >
            <div class="level-header">
              <span class="level-type">SELL</span>
              <span class="level-price">{{ formatPrice(price) }}</span>
            </div>
            <div class="level-details">
              <span class="level-amount">{{ level.amount }}</span>
              <div class="level-actions">
                <button
                  class="action-btn add-btn"
                  @click="addOrder(level.type, price)"
                  :disabled="isGoalAchieved"
                >+</button>
                <button
                  class="action-btn cancel-btn"
                  @click="cancelOrder(level.type, price)"
                  :disabled="isGoalAchieved"
                >-</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useTraderStore } from '@/store/app'
import { storeToRefs } from 'pinia'
import axios from 'axios'

const props = defineProps({
  isGoalAchieved: {
    type: Boolean,
    default: false,
  },
})

const traderStore = useTraderStore()
const { activeOrders, traderUuid } = storeToRefs(traderStore)

// Initialize active orders from backend on component mount
onMounted(async () => {
  try {
    const response = await axios.get(`/trader/${traderUuid.value}/market`)

    if (response.data.status === 'success') {
      const traderOrders = response.data.data.game_params?.active_orders || []
      activeOrders.value = traderOrders.filter((order) => order.trader_id === traderUuid.value)
    }
  } catch (error) {
    console.error('Error fetching active orders:', error)
  }
})

watch(
  activeOrders,
  (newOrders) => {
    saveActiveOrders(newOrders)
  },
  { deep: true },
)

const sortedOrderLevels = computed(() => {
  const orders = activeOrders.value
  const levels = { buy: {}, sell: {} }

  orders.forEach((order) => {
    const type = order.order_type === 1 ? 'buy' : 'sell'
    const price = order.price.toString()
    if (!levels[type][price]) {
      levels[type][price] = { type: order.order_type, amount: 0 }
    }
    levels[type][price].amount += order.amount
  })

  return {
    buy: Object.entries(levels.buy).sort(([a], [b]) => Number(b) - Number(a)),
    sell: Object.entries(levels.sell).sort(([a], [b]) => Number(a) - Number(b)),
  }
})

const maxAmount = computed(() => {
  const allAmounts = [
    ...Object.values(sortedOrderLevels.value.buy).map(([, level]) => level.amount),
    ...Object.values(sortedOrderLevels.value.sell).map(([, level]) => level.amount),
  ]
  return Math.max(...allAmounts, 1)
})

function formatPrice(price) {
  return Math.round(price).toString()
}

function addOrder(type, price) {
  if (!props.isGoalAchieved) {
    traderStore.addOrder({ order_type: type, price: Number(price), amount: 1 })
  }
}

function cancelOrder(type, price) {
  if (!props.isGoalAchieved) {
    const orderToCancel = activeOrders.value.find(
      (order) => order.order_type === type && order.price === Number(price),
    )
    if (orderToCancel) {
      traderStore.cancelOrder(orderToCancel.id)
    }
  }
}

const saveActiveOrders = (orders) => {
  localStorage.setItem(`activeOrders_${traderUuid.value}`, JSON.stringify(orders))
}
</script>

<style scoped>
.active-orders {
  font-family: var(--font-family);
  background: var(--color-bg-surface);
}

.orders-body {
  padding: 8px;
  overflow-y: auto;
  max-height: 300px;
}

.orders-columns {
  display: flex;
  gap: 8px;
}

.orders-col {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.order-level {
  padding: 6px 8px;
  margin-bottom: 3px;
  border-radius: var(--radius-sm);
}

.bid-level {
  border-left: 2px solid var(--color-bid);
}

.ask-level {
  border-left: 2px solid var(--color-ask);
}

.level-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.level-type {
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: var(--tracking-wider);
}

.level-price {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.level-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.level-amount {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.level-actions {
  display: flex;
  gap: 3px;
}

.action-btn {
  width: 20px;
  height: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-surface);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  line-height: 1;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.add-btn {
  color: var(--color-bid);
}

.cancel-btn {
  color: var(--color-ask);
}

.no-orders {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: 20px;
}

/* Scrollbar */
.orders-body::-webkit-scrollbar {
  width: 4px;
}

.orders-body::-webkit-scrollbar-track {
  background: transparent;
}

.orders-body::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}
</style>
