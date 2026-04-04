import { createApp } from 'vue'
import App from './App.vue'
import { registerPlugins } from '@/plugins'
import VueApexCharts from 'vue3-apexcharts'
import VueCountdown from '@chenfengyuan/vue-countdown'

// Design System - Import order matters
import './styles/design-tokens.css'
import './styles/components.css'
import './global.css'

import '@mdi/font/css/materialdesignicons.css'
import { Toaster } from 'vue-sonner'

// Create Vue app
const app = createApp(App)

// Explicitly enable Vue DevTools
app.config.devtools = true

// Use additional plugins not handled by registerPlugins
app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)
app.component('Toaster', Toaster)

// Register all main plugins (Vuetify, Pinia, Router, Motion)
registerPlugins(app)

app.mount('#app')
