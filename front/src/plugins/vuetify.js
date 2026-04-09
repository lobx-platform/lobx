/**
 * plugins/vuetify.js
 *
 * Trading Platform — Refined Minimalist Theme
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
          // Primary — Blue accent
          primary: '#0066FF',
          'primary-darken-1': '#0052CC',

          // Secondary
          secondary: '#666666',

          // Semantic colors
          error: '#cb2431',
          info: '#0066FF',
          success: '#22863a',
          warning: '#b08800',

          // Surface colors
          background: '#FAFAFA',
          surface: '#FFFFFF',
          'surface-variant': '#F5F5F5',

          // Text colors
          'on-background': '#1a1a1a',
          'on-surface': '#1a1a1a',
          'on-primary': '#FFFFFF',
        }
      }
    }
  },
  defaults: {
    VBtn: {
      variant: 'flat',
      rounded: 'md',
      elevation: 0,
    },
    VCard: {
      rounded: 'md',
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
