<template>
  <v-card height="100%" elevation="3" class="my-orders-card">
    <div class="orders-container">
      <div v-if="Object.keys(sortedOrderLevels).length === 0" class="no-orders-message">
        No active orders
      </div>
      <div v-else class="orders-columns">
        <div class="orders-column bid-column">
          <div class="order-levels-container">
            <div
              v-for="[price, level] in sortedOrderLevels.buy"
              :key="price"
              class="order-level bid"
            >
              <div class="order-header">
                <span class="order-type">BUY</span>
                <div class="price">{{ formatPrice(price) }}</div>
              </div>
              <div class="order-details">
                <div class="amount">Amount: {{ level.amount }}</div>
                <div class="order-actions">
                  <v-btn
                    icon
                    x-small
                    @click="addOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="success"
                    class="action-btn"
                  >
                    <v-icon small>mdi-plus</v-icon>
                  </v-btn>
                  <v-btn
                    icon
                    x-small
                    @click="cancelOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="error"
                    class="action-btn"
                  >
                    <v-icon small>mdi-minus</v-icon>
                  </v-btn>
                </div>
              </div>
              <v-progress-linear
                :value="(level.amount / maxAmount) * 100"
                color="success"
                height="2"
                class="amount-progress"
              ></v-progress-linear>
            </div>
          </div>
        </div>
        <div class="orders-column ask-column">
          <div class="order-levels-container">
            <div
              v-for="[price, level] in sortedOrderLevels.sell"
              :key="price"
              class="order-level ask"
            >
              <div class="order-header">
                <span class="order-type">SELL</span>
                <div class="price">{{ formatPrice(price) }}</div>
              </div>
              <div class="order-details">
                <div class="amount">Amount: {{ level.amount }}</div>
                <div class="order-actions">
                  <v-btn
                    icon
                    x-small
                    @click="addOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="success"
                    class="action-btn"
                  >
                    <v-icon small>mdi-plus</v-icon>
                  </v-btn>
                  <v-btn
                    icon
                    x-small
                    @click="cancelOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="error"
                    class="action-btn"
                  >
                    <v-icon small>mdi-minus</v-icon>
                  </v-btn>
                </div>
              </div>
              <v-progress-linear
                :value="(level.amount / maxAmount) * 100"
                color="error"
                height="2"
                class="amount-progress"
              ></v-progress-linear>
            </div>
          </div>
        </div>
      </div>
    </div>
  </v-card>
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
    // Get trader market info which includes active orders
    const response = await axios.get(`/trader/${traderUuid.value}/market`)

    if (response.data.status === 'success') {
      // Update store with active orders from backend
      const traderOrders = response.data.data.game_params?.active_orders || []
      activeOrders.value = traderOrders.filter((order) => order.trader_id === traderUuid.value)
    }
  } catch (error) {
    console.error('Error fetching active orders:', error)
  }
})

// Watch for changes in active orders and save them
watch(
  activeOrders,
  (newOrders) => {
    saveActiveOrders(newOrders)
  },
  { deep: true }
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
  return Math.round(price).toString() // Changed to round the price
}

function addOrder(type, price) {
  if (!props.isGoalAchieved) {
    traderStore.addOrder({ order_type: type, price: Number(price), amount: 1 })
  }
}

function cancelOrder(type, price) {
  if (!props.isGoalAchieved) {
    const orderToCancel = activeOrders.value.find(
      (order) => order.order_type === type && order.price === Number(price)
    )
    if (orderToCancel) {
      traderStore.cancelOrder(orderToCancel.id)
    }
  }
}

// Save active orders to localStorage
const saveActiveOrders = (orders) => {
  localStorage.setItem(`activeOrders_${traderUuid.value}`, JSON.stringify(orders))
}
</script>

<style scoped>
.my-orders-card {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-surface);
  font-family: var(--font-family);
}

.orders-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: var(--space-3);
}

.orders-columns {
  display: flex;
  gap: var(--space-2);
}

.orders-column {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.order-level {
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2);
  margin-bottom: var(--space-1-5);
  font-size: var(--text-sm);
  transition: border-color var(--transition-fast);
}

.order-level:hover {
  border-color: var(--color-border-strong);
}

.order-level.bid {
  border-left: 2px solid var(--color-bid);
}

.order-level.ask {
  border-left: 2px solid var(--color-ask);
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3px;
}

.order-type {
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: var(--tracking-wider);
}

.price {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-bright);
}

.order-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3px;
}

.amount {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.order-actions {
  display: flex;
  gap: 3px;
}

.action-btn {
  width: 20px;
  height: 20px;
}

.amount-progress {
  margin-top: 3px;
}

.no-orders-message {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: 20px;
}

.order-levels-container {
  max-height: 300px;
  overflow-y: auto;
  padding-right: 6px;
}

/* Scrollbar */
.order-levels-container::-webkit-scrollbar {
  width: 4px;
}

.order-levels-container::-webkit-scrollbar-track {
  background: transparent;
}

.order-levels-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.order-levels-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
