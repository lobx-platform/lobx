/**
 * Standalone Socket.IO module — NOT stored in Pinia state.
 *
 * Exports:
 *   socket        – the raw Socket.IO client instance (or null before connect)
 *   socketState   – reactive { connected } for UI binding
 *   connectSocket – creates and returns the socket
 *   disconnectSocket – tears it down
 *   emitSocket    – safe emit wrapper
 */
import { reactive } from 'vue'
import { io } from 'socket.io-client'
import mitt from 'mitt'

// ── Reactive connection state (safe to use in templates) ────────────────────
export const socketState = reactive({
  connected: false,
})

// ── Event bus — stores subscribe to the events they care about ──────────────
export const wsBus = mitt()

// ── The raw socket instance (NOT reactive — never put in Pinia state) ───────
let _socket = null
let _lastJoinedTrader = null

/**
 * All server events we want to forward through the bus.
 * Adding a new backend event only requires adding its name here.
 */
const ROUTED_EVENTS = [
  'time_update',
  'trader_count_update',
  'session_waiting',
  'waiting_room_update',
  'market_started',
  'market_status_update',
  'trader_status_update',
  'book_updated',
  'trading_started',
  'stop_trading',
  'closure',
  'filled_order',
  'transaction_update',
  'error',
  'ready_ack',
  'trader_id_confirmation',
]

/**
 * Create a Socket.IO connection and wire events to the bus.
 *
 * @param {string} traderUuid – trader ID to auto-join after connect
 * @param {{ labToken?: string, adminToken?: string, prolificPid?: string }} auth – credentials
 * @returns {object} the raw socket instance
 */
export function connectSocket(traderUuid, { labToken, adminToken, prolificPid } = {}) {
  // Tear down any stale connection first
  if (_socket) {
    _socket.disconnect()
    _socket = null
  }

  const baseUrl = import.meta.env.VITE_HTTP_URL || 'http://localhost:8000/'
  const url = new URL(baseUrl)
  const sioPath = (url.pathname.replace(/\/$/, '') || '') + '/socket.io/'

  const auth = {}
  if (labToken) auth.lab_token = labToken
  else if (adminToken) auth.admin_token = adminToken
  else if (prolificPid) auth.prolific_pid = prolificPid

  console.log(`[Socket.IO] Connecting to ${url.origin} path=${sioPath} auth=`, auth)
  _socket = io(url.origin, {
    auth,
    path: sioPath,
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 5,
    reconnectionDelay: 3000,
  })

  // ── Lifecycle events ──────────────────────────────────────────────────────
  _socket.on('connect', () => {
    console.log(`[Socket.IO] Connected! sid=${_socket.id}`)
    socketState.connected = true
    // Auto-rejoin market if we were in one (handles reconnect + re-init)
    if (_lastJoinedTrader) {
      console.log(`[Socket.IO] Auto-rejoining market for ${_lastJoinedTrader}`)
      _socket.emit('join_market', { trader_id: _lastJoinedTrader })
    }
  })

  _socket.on('disconnect', () => {
    socketState.connected = false
  })

  _socket.on('connect_error', (err) => {
    console.error(`[Socket.IO] Connection error:`, err.message)
    socketState.connected = false
  })

  // ── Route every server event through the mitt bus ─────────────────────────
  for (const event of ROUTED_EVENTS) {
    _socket.on(event, (payload) => {
      // Normalise: the bus always receives (eventName, payload)
      wsBus.emit(event, payload)
    })
  }

  // ── Reconnect: re-join the market room automatically ──────────────────────
  _socket.io.on('reconnect', () => {
    console.log('[Socket.IO] Reconnected')
    socketState.connected = true
    // Re-join market if we were in one
    if (_lastJoinedTrader) {
      _socket.emit('join_market', { trader_id: _lastJoinedTrader })
    }
  })

  return _socket
}

/**
 * Join a market room. Call this after /trading/start succeeds.
 */
export function joinMarket(traderId) {
  // Always set this so auto-rejoin works when socket connects/reconnects
  _lastJoinedTrader = traderId
  if (!_socket || !_socket.connected) {
    console.log('[Socket.IO] Not connected yet — will join market on connect')
    return
  }
  console.log(`[Socket.IO] Joining market for ${traderId}`)
  _socket.emit('join_market', { trader_id: traderId })
}

/**
 * Emit a message to the server. Maps legacy event names.
 */
export function emitSocket(type, data) {
  if (!_socket || !_socket.connected) return

  if (type === 'add_order') {
    _socket.emit('place_order', data)
  } else if (type === 'cancel_order') {
    _socket.emit('cancel_order', data)
  } else {
    _socket.emit(type, data)
  }
}

/**
 * Disconnect and clean up.
 */
export function disconnectSocket() {
  if (_socket) {
    _socket.disconnect()
    _socket = null
    socketState.connected = false
  }
}

/**
 * Access the raw socket (for read-only checks like `.connected`).
 */
export function getSocket() {
  return _socket
}
