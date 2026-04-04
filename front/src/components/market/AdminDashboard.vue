<template>
  <div class="admin-dashboard">
    <!-- Header Bar -->
    <header class="admin-header">
      <div class="admin-header-left">
        <div class="admin-logo-mark"></div>
        <div class="admin-title-block">
          <h1 class="admin-title">Control Panel</h1>
          <span class="admin-subtitle">London Trader Experiment Platform</span>
        </div>
      </div>
      <div class="admin-header-right">
        <div class="admin-indicator">
          <span class="admin-indicator-dot" :class="serverActive ? 'dot-live' : 'dot-off'"></span>
          <span class="admin-indicator-label">{{ serverActive ? 'Server Online' : 'Disconnected' }}</span>
        </div>
      </div>
    </header>

    <!-- Navigation + Content -->
    <div class="admin-body">
      <!-- Tab Rail -->
      <nav class="admin-rail">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="rail-tab"
          :class="{ 'rail-tab-active': activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          <span class="rail-tab-icon">{{ tab.icon }}</span>
          <span class="rail-tab-label">{{ tab.label }}</span>
        </button>
        <div class="rail-spacer"></div>
        <div class="rail-footer">
          <span class="rail-footer-text">v2.0</span>
        </div>
      </nav>

      <!-- Main Content -->
      <main class="admin-content">
        <ConfigTab
          v-if="activeTab === 'config'"
          :formState="formState"
          :formFields="formFields"
          :serverActive="serverActive"
          @update:formState="updateFormState"
        />
        <MarketsTab v-else-if="activeTab === 'markets'" :serverActive="serverActive" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '@/api/axios'
import ConfigTab from './admin/ConfigTab.vue'
import MarketsTab from './admin/MarketsTab.vue'

const tabs = [
  { value: 'config', label: 'Configuration', icon: '\u2699' },
  { value: 'markets', label: 'Markets', icon: '\u25CE' },
]

const activeTab = ref('config')
const formState = ref({
  throttle_settings: {
    HUMAN: { order_throttle_ms: 1000, max_orders_per_window: 2 },
    NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
    MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
  },
})
const formFields = ref([])
const serverActive = ref(false)

const updateFormState = (newState) => {
  formState.value = newState
}

const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_base_settings`),
    ])

    const defaultData = defaultsResponse.data.data
    const persistentSettings = persistentSettingsResponse.data.data

    formState.value = {}

    for (const [key, value] of Object.entries(defaultData)) {
      if (key !== 'throttle_settings') {
        formState.value[key] = persistentSettings[key] ?? value.default
        formFields.value.push({ name: key, ...value })
      }
    }

    const defaultThrottleSettings = {
      HUMAN: { order_throttle_ms: 100, max_orders_per_window: 1 },
      NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
      MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
      }

    formState.value.throttle_settings = persistentSettings.throttle_settings || defaultThrottleSettings
    serverActive.value = true
  } catch (error) {
    serverActive.value = false
    console.error('Failed to fetch data:', error)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.admin-dashboard {
  min-height: 100vh;
  background: var(--color-bg-page);
  display: flex;
  flex-direction: column;
}

/* ---- Header ---- */
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-5);
  background: var(--color-bg-surface);
  border-bottom: var(--border-width) solid var(--color-border);
  box-shadow: var(--shadow-xs);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.admin-header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.admin-logo-mark {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
  box-shadow: 0 2px 8px rgba(8, 145, 178, 0.25);
  position: relative;
}

.admin-logo-mark::after {
  content: '';
  position: absolute;
  inset: 5px;
  border: 2px solid rgba(255, 255, 255, 0.6);
  border-radius: 2px;
}

.admin-title-block {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.admin-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--tracking-tight);
  line-height: 1.2;
}

.admin-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  font-weight: var(--font-medium);
}

.admin-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.admin-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) var(--space-3);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-full);
  border: var(--border-width) solid var(--color-border);
}

.admin-indicator-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  background: var(--color-text-muted);
  transition: background var(--transition-base);
}

.admin-indicator-dot.dot-live {
  background: var(--color-success);
  box-shadow: 0 0 6px rgba(22, 163, 74, 0.4);
  animation: pulse-dot 2s ease-in-out infinite;
}

.admin-indicator-dot.dot-off {
  background: var(--color-error);
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.admin-indicator-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  letter-spacing: var(--tracking-wide);
}

/* ---- Body Layout ---- */
.admin-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ---- Rail Navigation ---- */
.admin-rail {
  width: 180px;
  min-width: 180px;
  background: var(--color-bg-surface);
  border-right: var(--border-width) solid var(--color-border);
  padding: var(--space-4) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.rail-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  background: transparent;
  border: var(--border-width) solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
  font-family: var(--font-family);
}

.rail-tab:hover {
  background: var(--color-bg-subtle);
  color: var(--color-text-primary);
}

.rail-tab-active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-color: rgba(8, 145, 178, 0.15);
  font-weight: var(--font-semibold);
}

.rail-tab-active:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.rail-tab-icon {
  font-size: var(--text-lg);
  line-height: 1;
  width: 20px;
  text-align: center;
}

.rail-tab-label {
  letter-spacing: var(--tracking-wide);
}

.rail-spacer {
  flex: 1;
}

.rail-footer {
  padding: var(--space-2) var(--space-3);
  border-top: var(--border-width) solid var(--color-border-light);
}

.rail-footer-text {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  letter-spacing: var(--tracking-wide);
}

/* ---- Main Content ---- */
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5);
  background: var(--color-bg-page);
}

/* ---- Responsive ---- */
@media (max-width: 960px) {
  .admin-body {
    flex-direction: column;
  }

  .admin-rail {
    width: 100%;
    min-width: auto;
    border-right: none;
    border-bottom: var(--border-width) solid var(--color-border);
    padding: var(--space-2) var(--space-3);
    flex-direction: row;
    align-items: center;
    overflow-x: auto;
  }

  .rail-spacer,
  .rail-footer {
    display: none;
  }

  .admin-content {
    padding: var(--space-3);
  }
}
</style>
