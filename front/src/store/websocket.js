import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    ws: null,
    isConnected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
  }),

  actions: {
    async initializeWebSocket(traderUuid) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        return // Already connected
      }

      const wsUrl = `${import.meta.env.VITE_WS_URL}trader/${traderUuid}`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = async (event) => {
        this.isConnected = true
        this.reconnectAttempts = 0

        // Add a small delay to ensure WebSocket is fully ready
        setTimeout(async () => {
          try {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              const authStore = useAuthStore()
              if (authStore.labToken) {
                this.ws.send(authStore.labToken)
              } else if (authStore.adminToken) {
                this.ws.send(authStore.adminToken)
              } else {
                this.ws.send('no-auth')
              }
            }
          } catch (error) {
            // Error sending authentication token
          }
        }, 100) // 100ms delay
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          // Error processing WebSocket message
        }
      }

      this.ws.onerror = (error) => {
        this.isConnected = false
      }

      this.ws.onclose = (event) => {
        this.isConnected = false

        // Don't auto-reconnect for session waiting (code 1000)
        if (event.code === 1000 && event.reason === 'Session waiting') {
          return
        }

        this.attemptReconnect(traderUuid)
      }
    },

    handleMessage(data) {
      // This will be overridden by the main store to route messages
    },

    async sendMessage(type, messageData) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const message = JSON.stringify({ type, data: messageData })
        this.ws.send(message)
      } else {
        // WebSocket is not open
      }
    },

    attemptReconnect(traderUuid) {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        setTimeout(() => {
          this.initializeWebSocket(traderUuid)
        }, this.reconnectInterval)
      } else {
        // Max reconnection attempts reached
      }
    },

    disconnect() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
        this.isConnected = false
        this.reconnectAttempts = 0
      }
    },
  },
})
