// store.js
import { defineStore } from 'pinia'
import axios from '@/api/axios'
import { useAuthStore } from './auth'
import { useMarketStore } from './market'
import { useWebSocketStore } from './websocket'
import { useUIStore } from './ui'

export const useTraderStore = defineStore('trader', {
  state: () => ({
    // Core trader data
    traderUuid: null,
    trader: {
      shares: 0,
      cash: 0,
      initial_shares: 0,
      pnl: 0,
      vwap: 0,
      sum_dinv: 0,
    },

    // Trading state
    currentTime: null,
    isTradingStarted: false,
    remainingTime: null,

    // Market and game data
    tradingMarketData: {},
    gameParams: {},
    formState: null,

    // Orders
    placedOrders: [],
    executedOrders: [],

    // Trader attributes and progress
    traderAttributes: null,
    traderProgress: 0,

    // Market participants
    currentHumanTraders: 0,
    expectedHumanTraders: 0,
    allTradersReady: false,
    readyCount: 0,

    // Session management
    sessionStatus: null,
    isWaitingForOthers: false,
    shouldRedirectToTrading: false,

    // Transaction tracking
    lastMatchedOrders: null,
  }),
  getters: {
    shares: (state) => state.trader.shares,
    cash: (state) => state.trader.cash,
    initial_shares: (state) => state.trader.initial_shares,
    pnl: (state) => state.trader.pnl,
    vwap: (state) => state.trader.vwap,
    sum_dinv: (state) => state.trader.sum_dinv,

    goalMessage: (state) => {
      if (!state.traderAttributes || state.traderAttributes.goal === 0) return null

      const goalAmount = state.traderAttributes.goal
      const successVerb = goalAmount > 0 ? 'buying' : 'selling'
      const currentDelta = goalAmount - state.traderProgress
      const remaining = Math.abs(currentDelta)
      const shareWord = remaining === 1 ? 'share' : 'shares'

      const action = currentDelta > 0 ? 'buy' : 'sell'
      if (remaining === 0) {
        return {
          text: `You have reached your goal of ${successVerb} ${Math.abs(goalAmount)} shares`,
          type: 'success',
        }
      }

      return {
        text: `You need to ${action} ${remaining} ${shareWord} to reach your goal`,
        type: 'warning',
      }
    },

    activeOrders: (state) => state.placedOrders.filter((order) => order.status === 'active'),
    pendingOrders: (state) => state.placedOrders.filter((order) => order.status === 'pending'),

    availableCash(state) {
      const lockedCash = this.activeOrders
        .filter((order) => order.order_type === 'BUY' || order.order_type === 1)
        .reduce((sum, order) => sum + (order.price * (order.amount || 1)), 0)
      return state.trader.cash - lockedCash
    },

    availableShares(state) {
      const lockedShares = this.activeOrders
        .filter((order) => order.order_type === 'SELL' || order.order_type === -1)
        .reduce((sum, order) => sum + (order.amount || 1), 0)
      return state.trader.shares - lockedShares
    },

    hasExceededMaxShortShares: (state) => {
      if (state.gameParams.max_short_shares < 0) return false
      return (
        state.trader.shares < 0 &&
        Math.abs(state.trader.shares) >= state.gameParams.max_short_shares
      )
    },

    hasExceededMaxShortCash: (state) => {
      if (state.gameParams.max_short_cash < 0) return false
      return state.trader.cash < 0 && Math.abs(state.trader.cash) >= state.gameParams.max_short_cash
    },

    hasReachedMaxActiveOrders(state) {
      return this.activeOrders.length >= state.gameParams.max_active_orders
    },

    getSnackState(state) {
      if (
        this.hasExceededMaxShortCash ||
        this.hasExceededMaxShortShares ||
        this.hasReachedMaxActiveOrders
      ) {
        return true
      }
      return false
    },
  },
  actions: {
    // Initialize stores and setup message routing
    initializeStores() {
      const wsStore = useWebSocketStore()
      wsStore.handleMessage = (data) => {
        if (data.type === 'trader_id_confirmation') {
          this.confirmTraderId(data.data)
        } else {
          this.handle_update(data)
        }
      }
    },

    // Delegate to market store
    updateExtraParams(data) {
      useMarketStore().updateExtraParams(data)
    },

    async fetchPersistentSettings() {
      try {
        const response = await axios.get(
          `${import.meta.env.VITE_HTTP_URL}admin/get_base_settings`
        )
        return response.data.data
      } catch (error) {
        console.error('Error fetching persistent settings:', error)
        throw error
      }
    },

    async updatePersistentSettings(settings) {
      try {
        await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_base_settings`, {
          settings,
        })
      } catch (error) {
        console.error('Error updating persistent settings:', error)
        throw error
      }
    },

    async initializeTradingSystem(persistentSettings) {
      try {
        const response = await axios.post('trading/initiate')
        this.tradingMarketData = response.data.data
        this.gameParams = persistentSettings
        this.formState = this.gameParams

        if (response.data.status === 'waiting') {
          this.isWaitingForOthers = response.data.data.isWaitingForOthers || true
        } else if (response.data.status === 'not_in_session') {
          this.isWaitingForOthers = false
        } else {
          this.isWaitingForOthers = response.data.data.isWaitingForOthers || false
        }
      } catch (error) {
        throw error
      }
    },

    async initializeTradingSystemWithPersistentSettings() {
      try {
        const persistentSettings = await this.fetchPersistentSettings()
        await this.initializeTradingSystem(persistentSettings)
      } catch (error) {
        console.error('Error initializing trading system with persistent settings:', error)
        if (error.response) {
          console.error('Response data:', error.response.data)
          console.error('Response status:', error.response.status)
        }
        throw error
      }
    },

    async getTraderAttributes(traderId) {
      try {
        const response = await axios.get(`trader_info/${traderId}`)

        if (response.data.status === 'success' || response.data.status === 'waiting' || response.data.status === 'not_in_session') {
          const newData = response.data.data
          const isFirstFetch = !this.traderAttributes
          const stateChanged = response.data.status !== this.sessionStatus

          if (isFirstFetch || stateChanged) {
            this.traderAttributes = newData
            this.sessionStatus = response.data.status
          } else {
            this.traderAttributes = {
              ...this.traderAttributes,
              all_attributes: newData.all_attributes,
              goal: this.traderAttributes.goal !== undefined ? this.traderAttributes.goal : newData.goal,
              goal_progress: this.traderAttributes.goal_progress !== undefined ? this.traderAttributes.goal_progress : newData.goal_progress,
            }
          }

          this.traderUuid = traderId

          if (response.data.status === 'waiting') {
            this.isWaitingForOthers = response.data.data.all_attributes?.isWaitingForOthers || true
          } else if (response.data.status === 'not_in_session') {
            this.isWaitingForOthers = false
          } else {
            this.isWaitingForOthers = response.data.data.all_attributes?.isWaitingForOthers || false
            if (isFirstFetch) {
              const filledOrders = this.traderAttributes.filled_orders || []
              this.traderProgress = this.calculateProgress(filledOrders)
            }
          }
        } else {
          throw new Error('Failed to fetch trader attributes')
        }
      } catch (error) {
        console.error('Error fetching trader attributes:', error)
        throw new Error('Failed to fetch trader attributes')
      }
    },

    async initializeTrader(traderUuid) {
      this.traderUuid = traderUuid

      try {
        await this.getTraderAttributes(traderUuid)

        try {
          const response = await axios.get(`trader/${traderUuid}/market`)
          if (response.data.status === 'success' || response.data.status === 'waiting' || response.data.status === 'not_in_session') {
            const marketData = response.data.data
            this.tradingMarketData = marketData

            if (response.data.status === 'waiting' || response.data.status === 'not_in_session') {
              this.$patch({
                currentHumanTraders: 1,
                expectedHumanTraders: marketData.game_params?.num_human_traders || 1,
                isWaitingForOthers: marketData.isWaitingForOthers || true,
              })
            } else {
              this.$patch({
                currentHumanTraders: marketData.human_traders.length,
                expectedHumanTraders: marketData.game_params.predefined_goals.length,
                isWaitingForOthers: marketData.isWaitingForOthers || false,
              })
            }
          }
        } catch (error) {
          console.error('Error fetching market data:', error)
        }

        this.initializeWebSocket()
      } catch (error) {
        console.error('Error initializing trader:', error)
      }
    },

    handle_update(data) {
      // Handle session waiting status
      if (data.type === 'session_waiting') {
        this.isWaitingForOthers = data.data.isWaitingForOthers || true
        return
      }

      // Handle market started notification
      if (data.type === 'market_started') {
        console.log('[WebSocket] Market started notification received')
        this.isWaitingForOthers = false
        this.isTradingStarted = true
        this.shouldRedirectToTrading = true
        return
      }

      // Handle trader count updates
      if (data.type === 'trader_count_update') {
        this.$patch({
          currentHumanTraders: data.data.current_human_traders,
          expectedHumanTraders: data.data.expected_human_traders,
        })
        return
      }

      // Handle time updates
      if (data.type === 'time_update') {
        this.$patch({
          currentTime: new Date(data.data.current_time),
          isTradingStarted: data.data.is_trading_started,
          remainingTime: data.data.remaining_time,
        })
        return
      }

      // Handle market status updates
      if (data.type === 'market_status_update') {
        this.allTradersReady = data.data.all_ready
        this.readyCount = data.data.ready_count
        return
      }

      // Handle trader status updates (sleep/wake)
      if (data.type === 'trader_status_update') {
        const paramName = data.param_name || `${data.trader_type}_trader_status`
        useMarketStore().updateExtraParams({
          [paramName]: data.trader_status
        })
        return
      }

      const {
        order_book,
        history,
        spread,
        midpoint,
        transaction_price,
        inventory,
        trader_orders,
        pnl,
        vwap,
        sum_dinv,
        initial_shares,
        matched_orders,
        type,
        goal,
        goal_progress,
      } = data

      // Update trader attributes - WebSocket has priority over polling
      if (goal !== undefined || goal_progress !== undefined) {
        if (!this.traderAttributes) {
          this.traderAttributes = {}
        }
        this.traderAttributes = {
          ...this.traderAttributes,
          goal: goal !== undefined ? goal : this.traderAttributes.goal,
          goal_progress:
            goal_progress !== undefined ? goal_progress : this.traderAttributes.goal_progress,
        }
      }

      // Handle transactions
      if (type === 'transaction_update' && matched_orders) {
        this.handleFilledOrder(matched_orders, transaction_price)
      }

      // Update market data via market store
      if (transaction_price || midpoint || spread || history !== undefined) {
        useMarketStore().updateMarketData({ spread, midpoint, history, transaction_price })
      }

      // Update market extra params
      if (transaction_price && midpoint && spread) {
        this.updateExtraParams({ transaction_price, midpoint, spread })
      }

      // Update order book via market store
      if (order_book) {
        useMarketStore().updateOrderBook(order_book, this.gameParams)
      }

      // Update trader orders
      if (trader_orders) {
        this.placedOrders = trader_orders.map((order) => ({
          ...order,
          order_type: order.order_type,
          status: 'active',
        }))
      }

      // Update trader data
      if (inventory) {
        const { shares, cash } = inventory
        this.trader.shares = shares
        this.trader.cash = cash
      }

      if (pnl !== undefined) {
        this.trader.pnl = pnl
      }

      if (initial_shares !== undefined) {
        this.trader.initial_shares = initial_shares
      }

      if (sum_dinv !== undefined) {
        this.trader.sum_dinv = sum_dinv
        this.updateExtraParams({ imbalance: sum_dinv })
      }

      if (vwap !== undefined) {
        this.trader.vwap = vwap
      }
    },

    handleFilledOrder(matched_orders, transaction_price) {
      this.lastMatchedOrders = matched_orders

      const isInvolvedInTransaction =
        matched_orders.bid_trader_id === this.traderUuid ||
        matched_orders.ask_trader_id === this.traderUuid

      useMarketStore().addTransaction({
        ...matched_orders,
        price: transaction_price,
        amount: matched_orders.transaction_amount,
        timestamp: new Date().toISOString(),
        isRelevantToTrader: isInvolvedInTransaction,
      })

      if (isInvolvedInTransaction) {
        const isBid = matched_orders.bid_trader_id === this.traderUuid
        const relevantOrderId = isBid ? matched_orders.bid_order_id : matched_orders.ask_order_id
        const isPassive =
          (isBid && matched_orders.initiator === 'ask') ||
          (!isBid && matched_orders.initiator === 'bid')

        this.updateOrderStatus(relevantOrderId, 'executed', isPassive)

        useUIStore().showMessage(
          `Trade executed: ${matched_orders.transaction_amount} @ ${transaction_price}`
        )
      }
    },

    updateOrderStatus(orderId, newStatus, isPassive) {
      const orderIndex = this.placedOrders.findIndex((order) => order.id === orderId)
      if (orderIndex !== -1) {
        const order = this.placedOrders[orderIndex]
        order.status = newStatus

        if (newStatus === 'executed' && !isPassive) {
          this.executedOrders.push({ ...order })
        }
        this.placedOrders.splice(orderIndex, 1)
      }
    },

    // WebSocket operations
    async initializeWebSocket() {
      this.initializeStores()
      await useWebSocketStore().initializeWebSocket(this.traderUuid)
    },

    async sendMessage(type, data) {
      await useWebSocketStore().sendMessage(type, data)
    },

    // UI operations
    checkLimits() {
      useUIStore().showLimitMessage(
        this.gameParams,
        this.hasReachedMaxActiveOrders,
        this.hasExceededMaxShortCash,
        this.hasExceededMaxShortShares
      )
    },

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

      this.sendMessage('add_order', message)
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
      const orderIndex = this.placedOrders.findIndex((order) => order.id === orderId)
      if (orderIndex !== -1) {
        this.sendMessage('cancel_order', { id: orderId })
        this.placedOrders.splice(orderIndex, 1)
      }
    },

    calculateProgress(filledOrders) {
      if (!filledOrders || !Array.isArray(filledOrders)) {
        return 0
      }
      return filledOrders.reduce((sum, order) => {
        const amount = order.amount || 1
        return sum + (order.order_type === 'BID' ? amount : -amount)
      }, 0)
    },

    confirmTraderId(data) {
      // Trader ID confirmation handled
    },

    async startTradingMarket() {
      try {
        const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}trading/start`)
        if (response.data.status === 'success') {
          if (response.data.all_ready) {
            this.isWaitingForOthers = false
            this.isTradingStarted = true

            setTimeout(async () => {
              try {
                await this.getTraderAttributes(this.traderUuid)
                const wsStore = useWebSocketStore()
                if (!wsStore.socket || !wsStore.socket.connected) {
                  await this.initializeWebSocket()
                }
              } catch (error) {
                console.error('Error transitioning to active state:', error)
              }
            }, 500)
          }
        }
        return response.data
      } catch (error) {
        console.error('Error starting trading market:', error)
        if (error.response) {
          console.error('Response data:', error.response.data)
          console.error('Response status:', error.response.status)
        }
        throw error
      }
    },

    clearStore() {
      this.$reset()
      try {
        useMarketStore().$reset()
        useUIStore().$reset()
        useWebSocketStore().disconnect()
      } catch (e) {
        // Stores might not be initialized yet
      }
    },
  },
})
