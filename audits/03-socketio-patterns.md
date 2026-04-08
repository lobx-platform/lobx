# Audit 03 — Socket.IO Integration Patterns

**Date:** 2026-04-08  
**Scope:** `front/src/store/websocket.js`, `front/src/store/app.js`, `back/api/socketio_server.py`, `back/traders/human_trader.py`, component usage in `TradingDashboard.vue` and `PlaceOrder.vue`

---

## 1. Current Problems

### 1.1 The `handleMessage` override is fragile and untraceable

```js
// websocket.js line 99-101
handleMessage(data) {
  // This will be overridden by the trader store to route messages
}
```

```js
// app.js line 132-141
initializeStores() {
  const wsStore = useWebSocketStore()
  wsStore.handleMessage = (data) => { ... }
}
```

The websocket store declares a no-op `handleMessage` action that gets **monkey-patched at runtime** by the trader store. Problems:

- **No type safety or contract** — any store can silently overwrite this, and there is no guarantee the override happens before the first message arrives.
- **Race condition** — if a Socket.IO event fires between `initializeWebSocket()` and `initializeStores()`, messages are silently dropped by the no-op.
- **Untraceable in devtools** — Pinia devtools show the action belongs to the websocket store, but the actual logic lives in the trader store.
- **Single-consumer only** — only one store can override `handleMessage`. If a second feature (e.g., admin monitoring, chat) needs to listen to events, it cannot.

### 1.2 Manual event routing duplicates what Socket.IO already provides

```js
// websocket.js lines 69-96
const routedEvents = [
  'time_update', 'trader_count_update', 'session_waiting',
  'market_started', ...
]
for (const event of routedEvents) {
  this.socket.on(event, (payload) => {
    // Normalize to { type, data } and forward to handleMessage
  })
}
```

This collapses Socket.IO's native **typed event system** back into a single-dispatch `{ type, data }` pattern — essentially re-implementing the raw WebSocket message bus that Socket.IO was meant to replace. Every new event requires:

1. Adding the string to `routedEvents` array
2. Adding an `if (data.type === '...')` branch in `handle_update`
3. Keeping the backend emit name in sync manually

### 1.3 `handle_update` is a 130-line if/else chain

`app.js` lines 283-417 contain a monolithic message dispatcher. Early events (`session_waiting`, `market_started`, etc.) return early, but the second half destructures ~15 fields from `data` and processes them unconditionally. This creates:

- **Tight coupling** — trader state, market state, and UI notifications are all mutated in one function.
- **Unclear data contracts** — the function expects `data.order_book`, `data.spread`, `data.inventory`, etc. but these fields are optional and their presence depends on which backend event fired.
- **No validation** — malformed payloads silently set `undefined` into state.

### 1.4 Backend sends bloated payloads

`human_trader.py` `send_message_to_client()` (lines 117-133) always sends **the full trader state** on every event — shares, cash, pnl, inventory, goal, order_book, initial_cash, initial_shares, sum_dinv, vwap, filled_orders, placed_orders — regardless of what actually changed. A simple `book_updated` event carries all trader financial data.

### 1.5 No reconnection state management

The websocket store tracks `reconnectAttempts` in state but never updates it. Socket.IO's built-in reconnection manager handles retries internally, but the store has no visibility into it. The `connect_error` handler just sets `isConnected = false` without surfacing the error to the UI or attempting recovery logic (like re-joining the market room after reconnect).

### 1.6 Stale socket reference in Pinia state

`this.socket` is stored as a Pinia state property, which means Vue's reactivity system wraps it in a Proxy. Socket.IO client instances are not designed to be reactive proxies — this can cause subtle issues with internal Socket.IO state and method calls on the proxied object.

---

## 2. Modern Socket.IO + Vue 3 Patterns

### 2.1 Official recommended pattern (socket.io/how-to/use-with-vue)

The official Socket.IO docs recommend a **standalone module** (`src/socket.js`) that exports both the socket instance and reactive connection state:

```js
// src/socket.js
import { reactive } from 'vue'
import { io } from 'socket.io-client'

export const state = reactive({
  connected: false,
})

export const socket = io('http://localhost:3000', {
  autoConnect: false, // connect manually after auth
})

socket.on('connect', () => { state.connected = true })
socket.on('disconnect', () => { state.connected = false })
```

Components import and use directly — no store needed for the socket itself.

### 2.2 Composable pattern (`useSocket`)

Wrap the singleton in a composable for dependency injection and lifecycle management:

```js
// composables/useSocket.js
import { onUnmounted } from 'vue'
import { socket, state } from '@/socket'

export function useSocket() {
  const listeners = []

  function on(event, handler) {
    socket.on(event, handler)
    listeners.push({ event, handler })
  }

  // Auto-cleanup when component unmounts
  onUnmounted(() => {
    listeners.forEach(({ event, handler }) => socket.off(event, handler))
  })

  return {
    socket,
    isConnected: computed(() => state.connected),
    on,
    emit: socket.emit.bind(socket),
  }
}
```

This gives each component **automatic listener cleanup** on unmount and avoids global listener leaks.

### 2.3 Reconnection best practices

Since Socket.IO v3+, reconnection events live on the **Manager** (`socket.io`), not the socket:

```js
socket.io.on('reconnect', (attempt) => {
  // Re-join room after reconnect
  socket.emit('join_market', { trader_id: traderId })
})

socket.io.on('reconnect_error', (error) => {
  // Surface to UI
})
```

The current code does not listen to manager-level events at all.

---

## 3. Pinia Store vs. Standalone Composable

### Recommendation: **Hybrid — standalone socket + Pinia for domain state**

| Concern | Where it belongs |
|---------|-----------------|
| Socket instance, connect/disconnect | Standalone module (`src/socket.js`) |
| Connection state (`isConnected`) | Reactive ref in the socket module |
| Listener registration/cleanup | `useSocket()` composable |
| Trader state (shares, cash, orders) | `useTraderStore` (Pinia) |
| Market state (order book, prices) | `useMarketStore` (Pinia) |
| Event-to-store binding | Per-store `subscribeToSocket()` action |

**Why not keep the socket in Pinia?**

1. **Proxy issues** — Pinia wraps state in Vue reactivity proxies. Socket.IO's client instance has internal state (buffers, ack callbacks, manager references) that breaks under proxying.
2. **Devtools noise** — the socket object serializes poorly in Pinia devtools, creating massive unreadable state snapshots.
3. **Single responsibility** — the socket is a transport layer, not application state. Pinia stores should hold data that drives the UI.
4. **Multi-store consumption** — multiple Pinia stores should be able to subscribe to socket events independently (trader store handles `filled_order`, market store handles `book_updated`, admin store handles `trader_status_update`).

---

## 4. Event Typing and Validation

Even without TypeScript, you can enforce contracts using JSDoc and runtime validation:

### 4.1 Event schema definitions

```js
// events/schemas.js

/** @typedef {'time_update'|'book_updated'|'filled_order'|'transaction_update'|...} ServerEvent */

/**
 * @typedef {Object} TimeUpdatePayload
 * @property {string} current_time - ISO datetime
 * @property {boolean} is_trading_started
 * @property {number|null} remaining_time - seconds
 */

/**
 * @typedef {Object} FilledOrderPayload
 * @property {Object} matched_orders
 * @property {number} transaction_price
 */

/** @type {Record<string, (payload: any) => boolean>} */
export const validators = {
  time_update: (p) => typeof p.current_time === 'string' && typeof p.is_trading_started === 'boolean',
  filled_order: (p) => p.matched_orders != null && typeof p.transaction_price === 'number',
  book_updated: (p) => p.order_book != null,
}
```

### 4.2 Validated listener wrapper

```js
function onValidated(event, handler) {
  socket.on(event, (payload) => {
    const validate = validators[event]
    if (validate && !validate(payload)) {
      console.warn(`[socket] invalid ${event} payload`, payload)
      return
    }
    handler(payload)
  })
}
```

### 4.3 Shared event registry (frontend + backend)

For a project this size, a shared JSON or JS file listing all events and their expected shapes — consumed by both Python (as documentation) and JS (as runtime validators) — prevents drift between backend emits and frontend listeners.

---

## 5. Multi-Room Support for Multi-Participant Sessions

### Current state

The backend already uses Socket.IO rooms correctly:

```python
# socketio_server.py line 201
await sio.enter_room(sid, market_id)

# line 345
await sio.emit(event, sanitized, room=market_id)
```

But the **frontend has no concept of rooms** — it assumes a single market connection per page load.

### What Alessio needs

Multi-participant sessions where an admin or observer can monitor multiple markets simultaneously require:

1. **Room-aware event handling** — payloads should include `market_id` so the frontend knows which market the data belongs to.
2. **Per-market state** — instead of a single `useTraderStore`, the store should support keyed state by `market_id`.
3. **Admin namespace** — a separate Socket.IO namespace (`/admin`) for observation and control, so admin connections don't interfere with trader sessions.

### Proposed room architecture

```
Default namespace "/"
  Room: market_{uuid_1}  →  traders in session 1
  Room: market_{uuid_2}  →  traders in session 2

Namespace "/admin"
  Room: monitor_all      →  admin dashboards
  Room: market_{uuid_1}  →  admin observing session 1
```

Frontend changes:
- `useSocket()` returns a `joinRoom(marketId)` / `leaveRoom(marketId)` pair
- Event handlers receive `marketId` as first argument (or payload includes it)
- Pinia stores use a `Map<marketId, MarketState>` pattern for multi-market support

Backend changes:
- Already structured for this. `_sessions[sid]` tracks `market_id`.
- Add `/admin` namespace with separate auth (already have `is_admin` flag).
- `emit_to_market()` helper already supports room-scoped emission.

---

## 6. Concrete Refactoring Plan

### Phase 1: Extract socket from Pinia (low risk, high value)

**Files:** new `front/src/socket.js`, modify `front/src/store/websocket.js`

1. Create `src/socket.js` exporting the raw socket instance + reactive `state.connected`.
2. Move socket creation logic out of the Pinia store.
3. The Pinia websocket store becomes a thin wrapper that re-exports `state.connected` (for backward compat with components using `wsStore.isConnected`).
4. Socket instance is no longer stored in Pinia state (fixes proxy issue).

### Phase 2: Replace handleMessage override with direct event subscriptions

**Files:** `front/src/store/app.js`, `front/src/store/market.js`

1. Delete `handleMessage` from websocket store.
2. Delete `initializeStores()` from trader store.
3. In trader store's `initializeWebSocket()`, subscribe directly:

```js
import { socket } from '@/socket'

async initializeWebSocket() {
  socket.on('time_update', (data) => this.handleTimeUpdate(data))
  socket.on('filled_order', (data) => this.handleFilledOrder(data))
  socket.on('book_updated', (data) => useMarketStore().updateOrderBook(data.order_book))
  // ...
}
```

4. Split `handle_update` into small, named handlers: `handleTimeUpdate`, `handleTraderCountUpdate`, `handleBookUpdated`, `handleTransactionUpdate`, etc.

### Phase 3: Create `useSocket` composable for components

**Files:** new `front/src/composables/useSocket.js`

1. Implement the composable pattern from Section 2.2.
2. Components that need direct socket access (e.g., `TradingDashboard.vue` watching connection state) use the composable instead of importing the store.
3. Add automatic listener cleanup on component unmount.

### Phase 4: Add reconnection handling

**Files:** `front/src/socket.js`

1. Listen to `socket.io.on('reconnect')` to re-emit `join_market`.
2. Store the current `traderUuid` and `marketId` in the socket module so reconnect can re-join automatically.
3. Surface reconnection attempts in UI (the `showErrorAlert` ref in `TradingDashboard.vue` already exists but is never triggered).

### Phase 5: Slim down backend payloads (optional, performance)

**Files:** `back/traders/human_trader.py`

1. `send_message_to_client` should only include fields relevant to each event type.
2. Define per-event payload builders: `_book_update_payload()`, `_transaction_payload()`, etc.
3. This reduces bandwidth and makes frontend event contracts clearer.

### Phase 6: Multi-room / admin namespace (when needed)

**Files:** `back/api/socketio_server.py`, new admin socket handlers

1. Add `/admin` namespace with its own auth.
2. Admin client connects to `/admin` namespace and joins specific market rooms to observe.
3. Frontend admin panel uses a separate `useAdminSocket()` composable.

---

## Summary of Priorities

| Priority | Change | Effort | Risk |
|----------|--------|--------|------|
| P0 | Move socket out of Pinia state (proxy fix) | Small | Low |
| P0 | Replace handleMessage override with direct subscriptions | Medium | Low |
| P1 | Split handle_update into named handlers | Medium | Low |
| P1 | Add reconnect + room re-join logic | Small | Low |
| P2 | Create useSocket composable | Small | Low |
| P2 | Add event validation layer | Small | Low |
| P3 | Slim backend payloads | Medium | Medium |
| P3 | Admin namespace for multi-room observation | Large | Medium |

---

## Sources

- [How to use with Vue 3 — Socket.IO official guide](https://socket.io/how-to/use-with-vue)
- [Dealing with Composables — Pinia docs](https://pinia.vuejs.org/cookbook/composables.html)
- [Composables vs. Provide/Inject vs. Pinia — Vue School](https://vueschool.io/articles/vuejs-tutorials/composables-vs-provide-inject-vs-pinia-when-to-use-what/)
- [Socket.IO Namespaces docs](https://socket.io/docs/v4/namespaces/)
- [Socket.IO Rooms docs](https://socket.io/docs/v3/rooms/)
- [The Socket instance (client-side) — Socket.IO](https://socket.io/docs/v3/client-socket-instance/)
- [Vue 3 Composition API + socket.io — DEV Community](https://dev.to/grawl/vue-3-composition-api-socketio-5den)
