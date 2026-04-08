/**
 * app.js — backward-compatible facade.
 *
 * `useTraderStore` now delegates to the split stores (trader.js + orders.js).
 * All existing component imports like `import { useTraderStore } from '@/store/app'`
 * continue to work unchanged.
 */
import { defineStore } from 'pinia'
import { useTraderCoreStore } from './trader'
import { useOrderStore } from './orders'

export const useTraderStore = defineStore('trader', {
  // No own state — everything is delegated
  state: () => ({}),

  getters: {
    // ── Delegated to traderCore ──────────────────────────────────────────
    traderUuid: () => useTraderCoreStore().traderUuid,
    trader: () => useTraderCoreStore().trader,
    shares: () => useTraderCoreStore().shares,
    cash: () => useTraderCoreStore().cash,
    initial_shares: () => useTraderCoreStore().initial_shares,
    pnl: () => useTraderCoreStore().pnl,
    vwap: () => useTraderCoreStore().vwap,
    sum_dinv: () => useTraderCoreStore().sum_dinv,
    currentTime: () => useTraderCoreStore().currentTime,
    isTradingStarted: () => useTraderCoreStore().isTradingStarted,
    remainingTime: () => useTraderCoreStore().remainingTime,
    tradingMarketData: () => useTraderCoreStore().tradingMarketData,
    gameParams: () => useTraderCoreStore().gameParams,
    formState: () => useTraderCoreStore().formState,
    traderAttributes: () => useTraderCoreStore().traderAttributes,
    traderProgress: () => useTraderCoreStore().traderProgress,
    currentHumanTraders: () => useTraderCoreStore().currentHumanTraders,
    expectedHumanTraders: () => useTraderCoreStore().expectedHumanTraders,
    allTradersReady: () => useTraderCoreStore().allTradersReady,
    readyCount: () => useTraderCoreStore().readyCount,
    sessionStatus: () => useTraderCoreStore().sessionStatus,
    isWaitingForOthers: () => useTraderCoreStore().isWaitingForOthers,
    shouldRedirectToTrading: () => useTraderCoreStore().shouldRedirectToTrading,

    // ── Delegated to orders ──────────────────────────────────────────────
    placedOrders: () => useOrderStore().placedOrders,
    executedOrders: () => useOrderStore().executedOrders,
    lastMatchedOrders: () => useOrderStore().lastMatchedOrders,
    activeOrders: () => useOrderStore().activeOrders,
    pendingOrders: () => useOrderStore().pendingOrders,
    availableCash: () => useOrderStore().availableCash,
    availableShares: () => useOrderStore().availableShares,
    hasExceededMaxShortShares: () => useOrderStore().hasExceededMaxShortShares,
    hasExceededMaxShortCash: () => useOrderStore().hasExceededMaxShortCash,
    hasReachedMaxActiveOrders: () => useOrderStore().hasReachedMaxActiveOrders,
    getSnackState: () => useOrderStore().getSnackState,

    // ── goalMessage (needs both stores) ──────────────────────────────────
    goalMessage() {
      const core = useTraderCoreStore()
      if (!core.traderAttributes || core.traderAttributes.goal === 0) return null

      const goalAmount = core.traderAttributes.goal
      const successVerb = goalAmount > 0 ? 'buying' : 'selling'
      const currentDelta = goalAmount - core.traderProgress
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
  },

  actions: {
    // ── Delegated to traderCore ──────────────────────────────────────────
    updateExtraParams(data) { useTraderCoreStore().updateExtraParams(data) },
    fetchPersistentSettings() { return useTraderCoreStore().fetchPersistentSettings() },
    updatePersistentSettings(settings) { return useTraderCoreStore().updatePersistentSettings(settings) },
    initializeTradingSystem(s) { return useTraderCoreStore().initializeTradingSystem(s) },
    initializeTradingSystemWithPersistentSettings() { return useTraderCoreStore().initializeTradingSystemWithPersistentSettings() },
    getTraderAttributes(id) { return useTraderCoreStore().getTraderAttributes(id) },
    initializeTrader(id) { return useTraderCoreStore().initializeTrader(id) },
    startTradingMarket() { return useTraderCoreStore().startTradingMarket() },
    initializeWebSocket() { return useTraderCoreStore().initializeWebSocket() },
    _subscribeToEvents() { return useTraderCoreStore()._subscribeToEvents() },
    calculateProgress(orders) { return useTraderCoreStore().calculateProgress(orders) },

    // ── Delegated to orders ──────────────────────────────────────────────
    addOrder(order) { useOrderStore().addOrder(order) },
    cancelOrder(id) { useOrderStore().cancelOrder(id) },
    checkLimits() { useOrderStore().checkLimits() },

    // ── Proxy setter for direct assignment patterns ────────────────────
    setShouldRedirectToTrading(val) { useTraderCoreStore().shouldRedirectToTrading = val },

    clearStore() {
      useTraderCoreStore().clearStore()
      useOrderStore().$reset()
    },

    // sendMessage still goes through websocket store for backward compat
    async sendMessage(type, data) {
      const { useWebSocketStore } = await import('./websocket')
      await useWebSocketStore().sendMessage(type, data)
    },
  },
})
