import { defineStore } from 'pinia'
import { io } from 'socket.io-client'
import { useAuthStore } from './auth'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    socket: null,
    isConnected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
  }),

  actions: {
    async initializeWebSocket(traderUuid) {
      if (this.socket && this.socket.connected) {
        return // Already connected
      }

      // Disconnect any stale socket
      if (this.socket) {
        this.socket.disconnect()
        this.socket = null
      }

      const authStore = useAuthStore()
      const auth = {}
      if (authStore.labToken) {
        auth.lab_token = authStore.labToken
      } else if (authStore.adminToken) {
        auth.admin_token = authStore.adminToken
      }

      // Derive the Socket.IO URL from the existing HTTP_URL env var
      // (Socket.IO client uses http(s), not ws(s))
      const baseUrl = import.meta.env.VITE_HTTP_URL || 'http://localhost:8000/'

      // Derive Socket.IO path from base URL (handles /api/ prefix from Docker root-path)
      const url = new URL(baseUrl)
      const sioPath = (url.pathname.replace(/\/$/, '') || '') + '/socket.io/'

      this.socket = io(url.origin, {
        auth,
        path: sioPath,
        transports: ['websocket', 'polling'],
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 3000,
      })

      this.socket.on('connect', () => {
        this.isConnected = true
        this.reconnectAttempts = 0

        // Automatically join the market after connecting
        this.socket.emit('join_market', { trader_id: traderUuid })
      })

      this.socket.on('disconnect', () => {
        this.isConnected = false
      })

      this.socket.on('connect_error', () => {
        this.isConnected = false
      })

      // ── Event routing ──────────────────────────────────────────────
      // Each server event is forwarded to the handleMessage callback,
      // wrapped in the same { type, data } shape the old WS used.

      const routedEvents = [
        'time_update',
        'trader_count_update',
        'session_waiting',
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
      ]

      for (const event of routedEvents) {
        this.socket.on(event, (payload) => {
          // The server may send the payload with a `type` field already
          // or it may be a raw dict. Normalise to { type, data/... }.
          if (payload && payload.type) {
            this.handleMessage(payload)
          } else {
            this.handleMessage({ type: event, data: payload })
          }
        })
      }
    },

    handleMessage(data) {
      // This will be overridden by the trader store to route messages
    },

    async sendMessage(type, messageData) {
      if (this.socket && this.socket.connected) {
        // Map legacy message types to Socket.IO events
        if (type === 'add_order') {
          this.socket.emit('place_order', messageData)
        } else if (type === 'cancel_order') {
          this.socket.emit('cancel_order', messageData)
        } else {
          this.socket.emit(type, messageData)
        }
      }
    },

    disconnect() {
      if (this.socket) {
        this.socket.disconnect()
        this.socket = null
        this.isConnected = false
        this.reconnectAttempts = 0
      }
    },
  },
})
