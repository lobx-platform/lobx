/**
 * Orders store — placed orders, executed orders, order lifecycle.
 *
 * Extracted from the old app.js god-store.
 */
import { defineStore } from 'pinia'
import { emitSocket } from '@/socket'
import { useTraderCoreStore } from './trader'
import { useUIStore } from './ui'

export const useOrderStore = defineStore('orders', {
  state: () => ({
    placedOrders: [],
    executedOrders: [],
    lastMatchedOrders: null,
  }),

  getters: {
    activeOrders: (state) => state.placedOrders.filter((o) => o.status === 'active'),
    pendingOrders: (state) => state.placedOrders.filter((o) => o.status === 'pending'),

    availableCash() {
      const trader = useTraderCoreStore()
      const lockedCash = this.activeOrders
        .filter((o) => o.order_type === 'BUY' || o.order_type === 1)
        .reduce((sum, o) => sum + (o.price * (o.amount || 1)), 0)
      return trader.trader.cash - lockedCash
    },

    availableShares() {
      const trader = useTraderCoreStore()
      const lockedShares = this.activeOrders
        .filter((o) => o.order_type === 'SELL' || o.order_type === -1)
        .reduce((sum, o) => sum + (o.amount || 1), 0)
      return trader.trader.shares - lockedShares
    },

    hasExceededMaxShortShares() {
      const trader = useTraderCoreStore()
      if (trader.gameParams.max_short_shares < 0) return false
      return (
        trader.trader.shares < 0 &&
        Math.abs(trader.trader.shares) >= trader.gameParams.max_short_shares
      )
    },

    hasExceededMaxShortCash() {
      const trader = useTraderCoreStore()
      if (trader.gameParams.max_short_cash < 0) return false
      return trader.trader.cash < 0 && Math.abs(trader.trader.cash) >= trader.gameParams.max_short_cash
    },

    hasReachedMaxActiveOrders() {
      const trader = useTraderCoreStore()
      return this.activeOrders.length >= trader.gameParams.max_active_orders
    },

    getSnackState() {
      return this.hasExceededMaxShortCash || this.hasExceededMaxShortShares || this.hasReachedMaxActiveOrders
    },
  },

  actions: {
    addOrder(order) {
      const normalizedOrderType = this.normalizeOrderType(order.order_type)

      const newOrder = {
        ...order,
        id: `pending_${Date.now()}`,
        status: 'pending',
        order_type: normalizedOrderType,
      }
      this.placedOrders.push(newOrder)

      const message = {
        type: normalizedOrderType === 'BUY' ? 1 : -1,
        price: order.price,
        amount: order.amount,
      }

      emitSocket('add_order', message)
    },

    normalizeOrderType(orderType) {
      if (typeof orderType === 'string') {
        return orderType.toUpperCase() === 'BUY' ? 'BUY' : 'SELL'
      } else if (typeof orderType === 'number') {
        return orderType === 1 ? 'BUY' : 'SELL'
      }
      throw new Error('Invalid order type')
    },

    cancelOrder(orderId) {
      const orderIndex = this.placedOrders.findIndex((o) => o.id === orderId)
      if (orderIndex !== -1) {
        emitSocket('cancel_order', { id: orderId })
        this.placedOrders.splice(orderIndex, 1)
      }
    },

    updateOrderStatus(orderId, newStatus, isPassive) {
      const orderIndex = this.placedOrders.findIndex((o) => o.id === orderId)
      if (orderIndex !== -1) {
        const order = this.placedOrders[orderIndex]
        order.status = newStatus

        if (newStatus === 'executed' && !isPassive) {
          this.executedOrders.push({ ...order })
        }
        this.placedOrders.splice(orderIndex, 1)
      }
    },

    /**
     * Sync placed orders from a full server snapshot (trader_orders field).
     */
    syncPlacedOrders(traderOrders) {
      this.placedOrders = traderOrders.map((order) => ({
        ...order,
        order_type: order.order_type,
        status: 'active',
      }))
    },

    checkLimits() {
      const trader = useTraderCoreStore()
      useUIStore().showLimitMessage(
        trader.gameParams,
        this.hasReachedMaxActiveOrders,
        this.hasExceededMaxShortCash,
        this.hasExceededMaxShortShares,
      )
    },
  },
})
