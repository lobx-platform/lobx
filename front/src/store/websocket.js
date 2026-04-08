/**
 * WebSocket store — thin backward-compatible wrapper around the standalone
 * socket module at @/socket.js.
 *
 * Components that use `useWebSocketStore().isConnected` keep working.
 * The actual socket instance is NOT stored in Pinia state (avoids Vue proxy issues).
 */
import { defineStore } from 'pinia'
import {
  socketState,
  connectSocket,
  disconnectSocket,
  emitSocket,
  getSocket,
} from '@/socket'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    // nothing — socket is external
  }),

  getters: {
    isConnected: () => socketState.connected,
    socket: () => getSocket(),
  },

  actions: {
    async initializeWebSocket(traderUuid) {
      const sock = getSocket()
      if (sock && sock.connected) return // already connected

      const { useAuthStore } = await import('./auth')
      const authStore = useAuthStore()

      connectSocket(traderUuid, {
        labToken: authStore.labToken,
        adminToken: authStore.adminToken,
        prolificPid: authStore.prolificPid,
      })
    },

    async sendMessage(type, data) {
      emitSocket(type, data)
    },

    disconnect() {
      disconnectSocket()
    },
  },
})
