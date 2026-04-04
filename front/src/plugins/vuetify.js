/**
 * plugins/vuetify.js
 *
 * Trading Platform — Dark Terminal Theme
 */

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Composables
import { createVuetify } from 'vuetify'

export default createVuetify({
  theme: {
    defaultTheme: 'terminal',
    themes: {
      terminal: {
        dark: true,
        colors: {
          // Primary — Teal/Cyan accent
          primary: '#22D3EE',
          'primary-darken-1': '#06B6D4',

          // Secondary
          secondary: '#94A3B8',

          // Semantic colors
          error: '#EF4444',
          info: '#3B82F6',
          success: '#22C55E',
          warning: '#F59E0B',

          // Surface colors
          background: '#0B1120',
          surface: '#111827',
          'surface-variant': '#1E293B',

          // Text colors
          'on-background': '#E2E8F0',
          'on-surface': '#E2E8F0',
          'on-primary': '#0F172A',
        }
      }
    }
  },
  defaults: {
    VBtn: {
      variant: 'flat',
      rounded: 'md',
    },
    VCard: {
      rounded: 'lg',
      elevation: 0,
    },
    VTextField: {
      variant: 'outlined',
      density: 'compact',
    },
    VSelect: {
      variant: 'outlined',
      density: 'compact',
    },
    VTextarea: {
      variant: 'outlined',
      density: 'compact',
    },
  }
})
