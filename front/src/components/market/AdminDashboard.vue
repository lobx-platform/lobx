<template>
  <div class="admin-dashboard">
    <!-- Header Bar -->
    <header class="admin-header">
      <h1 class="admin-title">Control Panel</h1>
      <span class="admin-status" :class="serverActive ? 'status-on' : 'status-off'">
        {{ serverActive ? 'Online' : 'Offline' }}
      </span>
    </header>

    <!-- Tab Navigation -->
    <nav class="admin-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="admin-tab"
        :class="{ 'admin-tab-active': activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </button>
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
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '@/api/axios'
import ConfigTab from './admin/ConfigTab.vue'
import MarketsTab from './admin/MarketsTab.vue'

const tabs = [
  { value: 'config', label: 'Config' },
  { value: 'markets', label: 'Markets' },
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
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.admin-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--tracking-tight);
}

.admin-status {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  letter-spacing: var(--tracking-wide);
}

.admin-status.status-on {
  color: var(--color-success);
}

.admin-status.status-off {
  color: var(--color-text-muted);
}

/* ---- Tab Navigation ---- */
.admin-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
  padding: 0 var(--space-5);
}

.admin-tab {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--font-family);
  transition: color var(--transition-fast);
  margin-bottom: -1px;
}

.admin-tab:hover {
  color: var(--color-text-primary);
}

.admin-tab-active {
  color: var(--color-text-primary);
  border-bottom-color: var(--color-text-primary);
  font-weight: var(--font-semibold);
}

/* ---- Main Content ---- */
.admin-content {
  flex: 1;
  padding: var(--space-5);
  background: var(--color-bg-page);
}
</style>
