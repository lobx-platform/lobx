<template>
  <div class="admin-dashboard">
    <!-- Header -->
    <header class="tp-page-header">
      <h1 class="tp-page-title">Trading Platform Admin</h1>
      <div class="tp-status">
        <span class="tp-status-dot" :class="serverActive ? 'tp-status-dot-success' : 'tp-status-dot-error'"></span>
        <span class="text-sm">{{ serverActive ? 'Connected' : 'Disconnected' }}</span>
      </div>
    </header>

    <!-- Main Layout: Tabs + Content + Export Panel -->
    <div class="main-layout">
      <!-- Left: Vertical Tabs -->
      <nav class="tabs-sidebar">
        <div class="tabs-list">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="tab-item"
            :class="{ 'tab-active': activeTab === tab.value }"
            @click="activeTab = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>
      </nav>

      <!-- Center: Tab Content -->
      <main class="tab-content">
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

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Tabs Sidebar */
.tabs-sidebar {
  width: 160px;
  background: var(--color-bg-surface);
  border-right: var(--border-width) solid var(--color-border);
  padding: var(--space-3) 0;
}

.tabs-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: 0 var(--space-2);
}

.tab-item {
  display: flex;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
}

.tab-item:hover {
  background: var(--color-bg-subtle);
  color: var(--color-text-primary);
}

.tab-active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.tab-active:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

/* Tab Content */
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  background: var(--color-bg-page);
}

/* Responsive */
@media (max-width: 960px) {
  .main-layout {
    flex-direction: column;
  }

  .tabs-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: var(--border-width) solid var(--color-border);
    padding: var(--space-2) 0;
  }

  .tabs-list {
    flex-direction: row;
    overflow-x: auto;
  }
}
</style>
