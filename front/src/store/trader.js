/**
 * Trader store — portfolio state (shares, cash, pnl, goal) and trader init.
 *
 * This is the refactored core of the old "app.js" god-store.
 * Components that were using `useTraderStore` from '@/store/app' still work
 * because app.js re-exports everything from here.
 */
import { defineStore } from 'pinia'
import axios from '@/api/axios'
import { wsBus } from '@/socket'
import { useMarketStore } from './market'
import { useUIStore } from './ui'
import { useOrderStore } from './orders'

export const useTraderCoreStore = defineStore('traderCore', {
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
  }),

  getters: {
    shares: (state) => state.trader.shares,
    cash: (state) => state.trader.cash,
    initial_shares: (state) => state.trader.initial_shares,
    pnl: (state) => state.trader.pnl,
    vwap: (state) => state.trader.vwap,
    sum_dinv: (state) => state.trader.sum_dinv,
  },

  actions: {
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

    calculateProgress(filledOrders) {
      if (!filledOrders || !Array.isArray(filledOrders)) {
        return 0
      }
      return filledOrders.reduce((sum, order) => {
        const amount = order.amount || 1
        return sum + (order.order_type === 'BID' ? amount : -amount)
      }, 0)
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
                const { useWebSocketStore } = await import('./websocket')
                const wsStore = useWebSocketStore()
                if (!wsStore.isConnected) {
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

    // ── WebSocket integration (subscribe via event bus) ──────────────────────
    async initializeWebSocket() {
      // Subscribe to server events via the mitt bus
      this._subscribeToEvents()

      const { useWebSocketStore } = await import('./websocket')
      await useWebSocketStore().initializeWebSocket(this.traderUuid)
    },

    _subscribeToEvents() {
      // Clear previous listeners to avoid duplicates on re-init
      wsBus.off('session_waiting')
      wsBus.off('market_started')
      wsBus.off('trader_count_update')
      wsBus.off('time_update')
      wsBus.off('market_status_update')
      wsBus.off('trader_status_update')
      wsBus.off('stop_trading')
      wsBus.off('closure')
      wsBus.off('book_updated')
      wsBus.off('transaction_update')
      wsBus.off('filled_order')
      wsBus.off('trader_id_confirmation')

      // Each event has its own focused handler
      wsBus.on('session_waiting', (data) => {
        this.isWaitingForOthers = data?.isWaitingForOthers || true
      })

      wsBus.on('market_started', () => {
        console.log('[WebSocket] Market started notification received')
        this.isWaitingForOthers = false
        this.isTradingStarted = true
        this.shouldRedirectToTrading = true
      })

      wsBus.on('trader_count_update', (data) => {
        this.$patch({
          currentHumanTraders: data.current_human_traders,
          expectedHumanTraders: data.expected_human_traders,
        })
      })

      wsBus.on('time_update', (data) => {
        this.$patch({
          currentTime: new Date(data.current_time),
          isTradingStarted: data.is_trading_started,
          remainingTime: data.remaining_time,
        })
      })

      wsBus.on('market_status_update', (data) => {
        this.allTradersReady = data.all_ready
        this.readyCount = data.ready_count
      })

      wsBus.on('trader_status_update', (data) => {
        const paramName = data.param_name || `${data.trader_type}_trader_status`
        useMarketStore().updateExtraParams({
          [paramName]: data.trader_status,
        })
      })

      // Unified handler for data-heavy events (book, inventory, transactions)
      const handleDataUpdate = (data) => {
        const {
          order_book, history, spread, midpoint, transaction_price,
          inventory, trader_orders, pnl, vwap, sum_dinv,
          initial_shares, matched_orders, type,
          goal, goal_progress,
        } = data

        // Update trader attributes
        if (goal !== undefined || goal_progress !== undefined) {
          if (!this.traderAttributes) this.traderAttributes = {}
          this.traderAttributes = {
            ...this.traderAttributes,
            goal: goal !== undefined ? goal : this.traderAttributes.goal,
            goal_progress: goal_progress !== undefined ? goal_progress : this.traderAttributes.goal_progress,
          }
        }

        // Handle transactions
        if (type === 'transaction_update' && matched_orders) {
          this._handleFilledOrder(matched_orders, transaction_price)
        }

        // Update market data
        if (transaction_price || midpoint || spread || history !== undefined) {
          useMarketStore().updateMarketData({ spread, midpoint, history, transaction_price })
        }

        if (transaction_price && midpoint && spread) {
          this.updateExtraParams({ transaction_price, midpoint, spread })
        }

        // Update order book
        if (order_book) {
          useMarketStore().updateOrderBook(order_book)
        }

        // Update trader orders
        if (trader_orders) {
          useOrderStore().syncPlacedOrders(trader_orders)
        }

        // Update trader data
        if (inventory) {
          this.trader.shares = inventory.shares
          this.trader.cash = inventory.cash
        }
        if (pnl !== undefined) this.trader.pnl = pnl
        if (initial_shares !== undefined) this.trader.initial_shares = initial_shares
        if (sum_dinv !== undefined) {
          this.trader.sum_dinv = sum_dinv
          this.updateExtraParams({ imbalance: sum_dinv })
        }
        if (vwap !== undefined) this.trader.vwap = vwap
      }

      // Market end events — navigate to summary
      wsBus.on('stop_trading', () => {
        console.log('[WebSocket] Market stopped')
        this.isTradingStarted = false
      })

      wsBus.on('closure', async () => {
        console.log('[WebSocket] Market closed — navigating to summary')
        const { default: NavigationService } = await import('@/services/navigation')
        NavigationService.onTradingEnded()
      })

      wsBus.on('book_updated', handleDataUpdate)
      wsBus.on('transaction_update', handleDataUpdate)
      wsBus.on('filled_order', handleDataUpdate)
      wsBus.on('trader_id_confirmation', () => {
        // Trader ID confirmation handled
      })
    },

    _handleFilledOrder(matched_orders, transaction_price) {
      const orderStore = useOrderStore()

      useMarketStore().addTransaction({
        ...matched_orders,
        price: transaction_price,
        amount: matched_orders.transaction_amount,
        timestamp: new Date().toISOString(),
        isRelevantToTrader: matched_orders.bid_trader_id === this.traderUuid ||
          matched_orders.ask_trader_id === this.traderUuid,
      })

      const isInvolvedInTransaction =
        matched_orders.bid_trader_id === this.traderUuid ||
        matched_orders.ask_trader_id === this.traderUuid

      if (isInvolvedInTransaction) {
        const isBid = matched_orders.bid_trader_id === this.traderUuid
        const relevantOrderId = isBid ? matched_orders.bid_order_id : matched_orders.ask_order_id
        const isPassive =
          (isBid && matched_orders.initiator === 'ask') ||
          (!isBid && matched_orders.initiator === 'bid')

        orderStore.updateOrderStatus(relevantOrderId, 'executed', isPassive)

        useUIStore().showMessage(
          `Trade executed: ${matched_orders.transaction_amount} @ ${transaction_price}`
        )
      }
    },

    clearStore() {
      this.$reset()
      try {
        useMarketStore().$reset()
        useUIStore().$reset()
        import('./websocket').then(({ useWebSocketStore }) => {
          useWebSocketStore().disconnect()
        })
      } catch (e) {
        // Stores might not be initialized yet
      }
    },
  },
})
