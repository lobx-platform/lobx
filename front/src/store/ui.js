import { defineStore } from 'pinia'

export const useUIStore = defineStore('ui', {
  state: () => ({
    showSnackbar: false,
    snackbarText: '',
    snackbarColor: 'info',
    snackbarTimeout: 5000,
  }),

  actions: {
    // Regular messages - no visual display (kept for compatibility)
    showMessage(text, color = 'info', timeout = 5000) {
      // Only log to console, don't show snackbar for info messages
      console.log(`[Info] ${text}`)
    },

    // Error messages - show in snackbar
    showError(text, timeout = 6000) {
      this.snackbarText = text
      this.snackbarColor = 'error'
      this.snackbarTimeout = timeout
      this.showSnackbar = true
    },

    // Success messages - show in snackbar (for explicit user actions like saving)
    showSuccess(text, timeout = 4000) {
      this.snackbarText = text
      this.snackbarColor = 'success'
      this.snackbarTimeout = timeout
      this.showSnackbar = true
    },

    hideMessage() {
      this.showSnackbar = false
      this.snackbarText = ''
    },

    showLimitMessage(
      gameParams,
      hasReachedMaxActiveOrders,
      hasExceededMaxShortCash,
      hasExceededMaxShortShares
    ) {
      if (hasReachedMaxActiveOrders) {
        this.showMessage(
          `You are allowed to have a maximum of ${gameParams.max_active_orders} active orders`
        )
      } else if (hasExceededMaxShortCash) {
        this.showMessage(`You are not allowed to short more than ${gameParams.max_short_cash} cash`)
      } else if (hasExceededMaxShortShares) {
        this.showMessage(
          `You are not allowed to short more than ${gameParams.max_short_shares} shares`
        )
      }
    },
  },
})
