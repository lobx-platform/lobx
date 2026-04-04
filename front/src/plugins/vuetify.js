/**
 * plugins/vuetify.js
 *
 * Trading Platform — Light Theme
 */

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Composables
import { createVuetify } from 'vuetify'

export default createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          // Primary — Teal/Cyan accent
          primary: '#0891B2',
          'primary-darken-1': '#0E7490',

          // Secondary
          secondary: '#475569',

          // Semantic colors
          error: '#DC2626',
          info: '#2563EB',
          success: '#16A34A',
          warning: '#D97706',

          // Surface colors
          background: '#F8FAFC',
          surface: '#FFFFFF',
          'surface-variant': '#F1F5F9',

          // Text colors
          'on-background': '#0F172A',
          'on-surface': '#0F172A',
          'on-primary': '#FFFFFF',
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
