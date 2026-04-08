# Audit 02 -- State Management Architecture

**Date:** 2026-04-08
**Scope:** `front/src/store/` (6 files), plugin setup, cross-store interactions

---

## 1. Current Problems

### 1.1 `app.js` is still the God Store (576 LOC)

`useTraderStore` conflates five distinct concerns into a single store:

| Concern | Lines (approx.) | Should live in |
|---|---|---|
| Trader portfolio state (shares, cash, pnl, vwap) | 10-60 | `store/trader.js` |
| Admin settings (fetch/update persistent settings) | 148-169 | `store/admin.js` or composable |
| Session lifecycle (waiting, redirect, ready count) | 171-280 | `store/session.js` (already exists!) |
| WebSocket message routing (`handle_update`) | 283-417 | `composables/useMessageRouter.js` |
| Order management (place, cancel, status tracking) | 449-527 | `store/orders.js` |

The store imports **four** sibling stores at module level and orchestrates all of them. This makes it the implicit "root store" -- exactly the Vuex pattern Pinia was designed to eliminate.

### 1.2 Circular / Entangled Import Graph

```
auth.js ──dynamic──> session.js ──dynamic──> auth.js   (circular)
app.js ──static───> auth.js, market.js, websocket.js, ui.js
websocket.js ──static──> auth.js
```

Both `auth` and `session` use `import('./other').then(...)` to break the cycle at runtime. This works but is fragile:
- The dynamic import creates a **race condition** if `syncToSessionStore()` fires before the session store is hydrated from localStorage.
- It prevents tree-shaking and makes the dependency graph invisible to tooling.

### 1.3 Manual localStorage vs `persist` Config -- Both Active, Neither Working Fully

`pinia-plugin-persistedstate` is **not installed** (absent from `package.json`). Yet two stores declare `persist` config:

- **`auth.js`** -- has `persist: { enabled: true, strategies: [...] }` (dead config, no plugin to read it)
- **`session.js`** -- has `persist` config AND manual `saveToLocalStorage()`/`loadFromLocalStorage()` methods

The comment on line 202 of `session.js` says it all:
> "If pinia-plugin-persistedstate is installed, this will work automatically. Otherwise, call saveToLocalStorage() manually after state changes"

Result: `auth` state is **not** persisted (the manual `localStorage.removeItem('auth')` in logout targets a key that nothing writes). `session` state **is** persisted, but only because manual calls exist. This is a maintenance trap.

### 1.4 WebSocket Message Routing via Monkey-Patching

In `app.js` line 134, the trader store **overwrites** the websocket store's `handleMessage` method:

```js
wsStore.handleMessage = (data) => { ... }
```

This is a monkey-patch, not a contract. Any code calling `useWebSocketStore().handleMessage()` before `initializeStores()` gets the no-op default. After, it gets the trader store's version. The coupling is invisible and untestable.

### 1.5 Duplicated State Across Stores

| Field | `auth.js` | `session.js` | `app.js` |
|---|---|---|---|
| `traderId` | yes | yes | yes (`traderUuid`) |
| `marketId` | yes | yes | -- |
| `labToken` | yes | yes | -- |
| `isWaitingForOthers` | -- | (implied by `status`) | yes |

Three stores track `traderId` independently. The `syncToSessionStore()` action in auth tries to keep them in sync, but nothing guarantees consistency. A single source of truth is needed.

### 1.6 Options API Stores Throughout

All six stores use the Options API syntax (`state/getters/actions` object). This works but forfeits:
- Composable reuse inside stores (e.g., `useLocalStorage` from VueUse)
- Watchers within stores
- Cleaner TypeScript inference
- Ability to use `storeToRefs()` ergonomically

---

## 2. Modern Pinia Patterns (2025-2026)

### 2.1 Setup Stores over Options Stores

The Pinia docs and community consensus (2025+) recommend **setup stores** for non-trivial logic:

```js
export const useTraderStore = defineStore('trader', () => {
  // State
  const shares = ref(0)
  const cash = ref(0)

  // Getters
  const pnl = computed(() => /* ... */)

  // Actions
  function placeOrder(order) { /* ... */ }

  return { shares, cash, pnl, placeOrder }
})
```

Benefits: you can use `watch()`, `watchEffect()`, VueUse composables, and other setup stores directly. No `this` context ambiguity.

### 2.2 Domain-Driven Store Splitting

One store per bounded context, not per "layer":

```
store/
  trader.js      -- portfolio state (shares, cash, pnl)
  orders.js      -- placed/executed orders, order lifecycle
  market.js      -- order book, price history, transactions
  session.js     -- auth + session lifecycle (merge current auth + session)
  connection.js  -- Socket.IO connection state only
  ui.js          -- snackbar, routing hints
```

### 2.3 `pinia-plugin-persistedstate` (v4+)

Install once, declare what to persist per-store. Eliminates all manual localStorage code:

```js
// plugins/index.js
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
```

```js
// In any store:
persist: {
  pick: ['traderId', 'labToken', 'adminToken'],
  storage: localStorage,
}
```

### 2.4 Store Composition via Direct Import (No Monkey-Patching)

Stores should call each other inside actions, not at module scope:

```js
// orders.js
export const useOrderStore = defineStore('orders', () => {
  function placeOrder(order) {
    const connection = useConnectionStore()  // called inside action
    connection.emit('place_order', order)
  }
  return { placeOrder }
})
```

### 2.5 Event Bus Pattern for WebSocket Messages

Instead of a monkey-patched `handleMessage`, use a lightweight event emitter or `mitt`:

```js
// lib/eventBus.js
import mitt from 'mitt'
export const wsBus = mitt()
```

Each store subscribes to only the events it cares about. The connection store emits to the bus. Zero coupling.

---

## 3. Recommended Store Architecture

### 3.1 Target File Structure

```
front/src/
  store/
    index.js              -- createPinia + plugin registration
    trader.js             -- setup store: shares, cash, pnl, goal tracking
    orders.js             -- setup store: placedOrders, executedOrders, place/cancel
    market.js             -- (keep, already well-scoped)
    session.js            -- merge auth + session into one store
    connection.js         -- Socket.IO lifecycle only (connect/disconnect/reconnect)
    ui.js                 -- (keep, already small)
  composables/
    useMessageRouter.js   -- subscribe to wsBus, dispatch to correct store
  lib/
    eventBus.js           -- mitt instance for WS events
```

### 3.2 Single Source of Truth for Identity

Merge `auth.js` and `session.js` into one `session.js`:

```js
// store/session.js (setup store)
export const useSessionStore = defineStore('session', () => {
  // Identity -- single source of truth
  const traderId = ref(null)
  const marketId = ref(null)
  const user = ref(null)
  const isAdmin = ref(false)
  const labToken = ref(null)
  const adminToken = ref(null)

  // Session lifecycle
  const status = ref('unknown')
  const onboardingStep = ref(0)
  const marketsCompleted = ref(0)

  // Computed
  const isAuthenticated = computed(() => !!user.value)
  const canTrade = computed(() => status.value === 'trading')

  // Actions
  async function labLogin(token) { /* ... */ }
  async function logout() {
    user.value = null
    traderId.value = null
    // ... single place to clear everything
  }

  return {
    traderId, marketId, user, isAdmin, labToken, adminToken,
    status, onboardingStep, marketsCompleted,
    isAuthenticated, canTrade,
    labLogin, logout,
  }
}, {
  persist: {
    pick: ['traderId', 'marketId', 'labToken', 'adminToken', 'isAdmin',
           'status', 'onboardingStep', 'marketsCompleted'],
  }
})
```

### 3.3 Extract Orders Store

```js
// store/orders.js
export const useOrderStore = defineStore('orders', () => {
  const placed = ref([])
  const executed = ref([])

  const active = computed(() => placed.value.filter(o => o.status === 'active'))
  const pending = computed(() => placed.value.filter(o => o.status === 'pending'))

  function place(order) {
    const normalized = normalizeType(order.order_type)
    placed.value.push({ ...order, id: `pending_${Date.now()}`, status: 'pending', order_type: normalized })
    useConnectionStore().emit('place_order', {
      type: normalized === 'BUY' ? 1 : -1,
      price: order.price,
      amount: order.amount,
    })
  }

  function cancel(orderId) {
    const idx = placed.value.findIndex(o => o.id === orderId)
    if (idx !== -1) {
      useConnectionStore().emit('cancel_order', { id: orderId })
      placed.value.splice(idx, 1)
    }
  }

  function handleFill(matchedOrders, price) {
    // ... move from placed to executed
  }

  return { placed, executed, active, pending, place, cancel, handleFill }
})
```

### 3.4 Slim Down Trader Store

```js
// store/trader.js
export const useTraderStore = defineStore('trader', () => {
  const shares = ref(0)
  const cash = ref(0)
  const initialShares = ref(0)
  const pnl = ref(0)
  const vwap = ref(0)
  const sumDinv = ref(0)
  const goal = ref(0)
  const goalProgress = ref(0)

  const goalMessage = computed(() => {
    if (goal.value === 0) return null
    const remaining = Math.abs(goal.value - goalProgress.value)
    if (remaining === 0) return { text: `Goal reached`, type: 'success' }
    const action = (goal.value - goalProgress.value) > 0 ? 'buy' : 'sell'
    return { text: `${action} ${remaining} more`, type: 'warning' }
  })

  function updateInventory({ shares: s, cash: c }) {
    shares.value = s
    cash.value = c
  }

  return { shares, cash, initialShares, pnl, vwap, sumDinv, goal, goalProgress, goalMessage, updateInventory }
})
```

---

## 4. Socket.IO Integration Pattern

### 4.1 Current: Centralized Dispatch (Fragile)

```
WebSocketStore.on('*') --> handleMessage (monkey-patched) --> TraderStore.handle_update()
  --> manually calls MarketStore, UIStore, etc.
```

All messages flow through `app.js handle_update()` -- a 130-line if/else chain. Adding a new event type requires editing the God Store.

### 4.2 Recommended: Event Bus + Store Subscriptions

```
ConnectionStore.on('*') --> wsBus.emit(type, payload)
                              |
         +--------------------+--------------------+
         |                    |                    |
   TraderStore           OrderStore           MarketStore
   listens to:           listens to:          listens to:
   - inventory_update    - transaction_update  - book_updated
   - goal_update         - filled_order        - time_update
```

Implementation:

```js
// lib/eventBus.js
import mitt from 'mitt'
export const wsBus = mitt()

// store/connection.js
export const useConnectionStore = defineStore('connection', () => {
  const socket = shallowRef(null)
  const isConnected = ref(false)

  function connect(traderId) {
    const session = useSessionStore()
    const s = io(baseUrl, { auth: { lab_token: session.labToken } })

    s.on('connect', () => { isConnected.value = true })
    s.on('disconnect', () => { isConnected.value = false })

    // Route ALL events through the bus
    const events = ['book_updated', 'transaction_update', 'time_update',
                    'market_started', 'session_waiting', 'trader_count_update',
                    'market_status_update', 'trader_status_update']
    for (const evt of events) {
      s.on(evt, (payload) => wsBus.emit(evt, payload))
    }

    socket.value = s
  }

  function emit(event, data) {
    socket.value?.emit(event, data)
  }

  function disconnect() {
    socket.value?.disconnect()
    socket.value = null
    isConnected.value = false
  }

  return { socket, isConnected, connect, emit, disconnect }
})
```

Each consuming store subscribes in a `setup` composable or an `onAction` hook:

```js
// composables/useMessageRouter.js
export function useMessageRouter() {
  const trader = useTraderStore()
  const orders = useOrderStore()
  const market = useMarketStore()

  wsBus.on('book_updated', (payload) => {
    market.updateOrderBook(payload.order_book, trader.gameParams)
  })

  wsBus.on('transaction_update', (payload) => {
    if (payload.matched_orders) {
      orders.handleFill(payload.matched_orders, payload.transaction_price)
    }
    market.updateMarketData(payload)
  })

  wsBus.on('time_update', (payload) => {
    trader.updateTime(payload)
  })

  // ... one handler per event type, clean and testable
}
```

Call `useMessageRouter()` once in the root component or when entering the trading view.

### 4.3 Why Not Polling?

The platform already uses Socket.IO for real-time order book updates. Polling would introduce latency in a trading context where milliseconds matter for user experience. Keep the event-driven approach, just decouple the routing.

---

## 5. Concrete Refactoring Plan

### Phase 1: Install persistence plugin & fix localStorage (1 hour)

1. `bun add pinia-plugin-persistedstate`
2. Update `plugins/index.js`:
   ```js
   import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
   const pinia = createPinia()
   pinia.use(piniaPluginPersistedstate)
   app.use(pinia)
   ```
3. Remove all manual `saveToLocalStorage()` / `loadFromLocalStorage()` from `session.js`
4. Remove `localStorage.removeItem('auth')` from `auth.js` logout
5. Update `persist` config in both stores to use v4 syntax (`pick` instead of `strategies`)
6. Verify auth survives page reload

### Phase 2: Merge auth + session stores (2 hours)

1. Create new `store/session.js` (setup store) combining both
2. Move `traderId`, `labToken`, `adminToken`, `user`, `isAdmin` from `auth` into the merged store
3. Update all 12+ import sites (`grep -r useAuthStore`)
4. Delete `auth.js`
5. Eliminate the circular dynamic imports entirely

### Phase 3: Extract orders store (1.5 hours)

1. Create `store/orders.js` with `placed`, `executed`, `place()`, `cancel()`, `handleFill()`
2. Move `placedOrders`, `executedOrders`, `addOrder()`, `cancelOrder()`, `updateOrderStatus()` from `app.js`
3. Move order-related getters (`activeOrders`, `pendingOrders`, `availableCash`, `availableShares`, limit checks)
4. Update `TradingDashboard.vue` and order form components

### Phase 4: Event bus for WebSocket messages (2 hours)

1. `bun add mitt`
2. Create `lib/eventBus.js`
3. Rename `websocket.js` to `connection.js`, convert to setup store, emit to bus instead of `handleMessage`
4. Create `composables/useMessageRouter.js`
5. Remove the 130-line `handle_update()` from `app.js`
6. Remove `initializeStores()` monkey-patch

### Phase 5: Convert remaining stores to setup syntax (1 hour)

1. Convert `trader.js` (the slimmed-down version) to setup store
2. Convert `market.js` to setup store
3. Convert `ui.js` to setup store
4. Ensure `storeToRefs()` works in all components

### Phase 6: Move admin API calls out of trader store (30 min)

1. Move `fetchPersistentSettings` / `updatePersistentSettings` to a composable (`composables/useAdminSettings.js`) or dedicated `store/admin.js`
2. These are only called from the admin panel -- they do not belong in the trader store

### Estimated Total: ~8 hours

### Dependency Order

```
Phase 1 (persistence) -- no breaking changes, do first
    |
Phase 2 (merge auth+session) -- biggest cross-cutting change
    |
Phase 3 (extract orders) + Phase 6 (admin) -- can run in parallel
    |
Phase 4 (event bus) -- depends on Phase 3 for order handling
    |
Phase 5 (setup syntax) -- cosmetic, do last
```

---

## Sources

- [Building Modular Store Architecture with Pinia in Large Vue Apps](https://medium.com/@vasanthancomrads/building-modular-store-architecture-with-pinia-in-large-vue-apps-0131e3d05430)
- [Vue Best Practices in 2026: Architecting for Speed, Scale, and Sanity](https://onehorizon.ai/blog/vue-best-practices-in-2026-architecting-for-speed-scale-and-sanity)
- [Pinia: Defining a Store](https://pinia.vuejs.org/core-concepts/)
- [Pinia: Composing Stores](https://pinia.vuejs.org/cookbook/composing-stores.html)
- [Pinia Tip: Use Setup Stores for More Flexibility](https://mokkapps.de/vue-tips/pinia-use-setup-stores-for-more-flexibility)
- [How to use Socket.IO with Vue 3](https://socket.io/how-to/use-with-vue)
- [Best Practices when using Pinia with Vue 3 and TypeScript](https://seanwilson.ca/blog/pinia-vue-best-practices.html)
- [Vue 3 + TypeScript Best Practices: 2025 Enterprise Architecture Guide](https://eastondev.com/blog/en/posts/dev/20251124-vue3-typescript-best-practices/)
