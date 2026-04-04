<template>
  <div class="markets-tab">

    <!-- ===== Active Markets ===== -->
    <div class="config-section">
      <div class="section-header">
        <div class="section-header-line"></div>
        <h2 class="section-title">Active Markets</h2>
        <span class="market-count" :class="{ 'market-count-live': activeSessions.length > 0 }">
          {{ activeSessions.length }}
        </span>
      </div>

      <div class="config-card">
        <div class="config-card-body" v-if="activeSessions.length === 0">
          <div class="empty-state">
            <span class="empty-state-icon">&#x25CB;</span>
            <span class="empty-state-text">No active markets</span>
          </div>
        </div>
        <div v-else class="markets-table-wrap">
          <v-data-table
            :headers="marketHeaders"
            :items="activeSessions"
            :items-per-page="5"
            density="compact"
            no-data-text="No active markets"
          >
            <template v-slot:item.market_id="{ item }">
              <span class="market-id">{{ formatMarketId(item.market_id) }}</span>
            </template>

            <template v-slot:item.status="{ item }">
              <span class="status-pill" :class="getStatusClass(item.status)">
                <span class="status-dot"></span>
                {{ item.status }}
              </span>
            </template>

            <template v-slot:item.member_ids="{ item }">
              <span class="member-count">
                {{ item.member_ids?.length || 0 }}
              </span>
            </template>

            <template v-slot:item.actions="{ item }">
              <button
                class="tp-btn tp-btn-sm tp-btn-secondary"
                :disabled="item.status === 'active' || !item.member_ids?.length"
                @click="forceStartSession(item.market_id)"
              >
                Start
              </button>
            </template>
          </v-data-table>
        </div>
      </div>
    </div>

    <!-- ===== AI-Only Market Runner ===== -->
    <div class="config-section">
      <div class="section-header">
        <div class="section-header-line"></div>
        <h2 class="section-title">AI-Only Market Runner</h2>
      </div>

      <div class="config-card">
        <div class="config-card-header">
          <span class="config-card-tag">Headless Batch</span>
        </div>
        <div class="config-card-body">
          <p class="helper-text">
            Run markets with only AI traders for testing and data collection.
          </p>

          <div class="batch-controls">
            <v-text-field
              v-model.number="batchConfig.numMarkets"
              label="Markets"
              type="number"
              min="1"
              max="10"
              hint="1-10 per batch"
              persistent-hint
              density="compact"
              variant="outlined"
            />
            <v-text-field
              v-model.number="batchConfig.startTreatment"
              label="Start Treatment"
              type="number"
              min="0"
              hint="Treatment index"
              persistent-hint
              density="compact"
              variant="outlined"
            />
          </div>

          <div class="batch-options">
            <v-switch
              v-model="batchConfig.parallel"
              label="Run in Parallel"
              color="primary"
              hide-details
              density="compact"
            />
            <v-text-field
              v-if="!batchConfig.parallel"
              v-model.number="batchConfig.delaySeconds"
              label="Delay (s)"
              type="number"
              min="1"
              max="60"
              hide-details
              density="compact"
              variant="outlined"
              style="max-width: 140px"
            />
          </div>

          <button
            class="tp-btn tp-btn-primary tp-btn-lg batch-start-btn"
            @click="startHeadlessBatch"
            :disabled="!serverActive || startingBatch"
          >
            {{ startingBatch ? 'Starting...' : `Start ${batchConfig.numMarkets} AI-Only Market${batchConfig.numMarkets > 1 ? 's' : ''}` }}
          </button>

          <!-- Running Sessions -->
          <div v-if="runningSessions.length > 0" class="sessions-group">
            <span class="sessions-label">Running</span>
            <div class="sessions-list">
              <span
                v-for="session in runningSessions"
                :key="session"
                class="session-chip session-chip-running"
              >
                <span class="session-chip-dot"></span>
                {{ formatSessionId(session) }}
              </span>
            </div>
          </div>

          <!-- Completed Sessions -->
          <div v-if="completedSessions.length > 0" class="sessions-group">
            <span class="sessions-label">Completed</span>
            <div class="sessions-list">
              <span
                v-for="session in completedSessions.slice(0, 5)"
                :key="session"
                class="session-chip session-chip-done"
              >
                {{ formatSessionId(session) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '@/api/axios'
import { useUIStore } from '@/store/ui'

const props = defineProps({
  serverActive: { type: Boolean, required: true },
})

const uiStore = useUIStore()

const activeSessions = ref([])
const runningSessions = ref([])
const completedSessions = ref([])
const startingBatch = ref(false)

const batchConfig = ref({
  numMarkets: 3,
  startTreatment: 0,
  parallel: true,
  delaySeconds: 5,
})

const marketHeaders = [
  { title: 'Market ID', key: 'market_id' },
  { title: 'Status', key: 'status' },
  { title: 'Members', key: 'member_ids' },
  { title: '', key: 'actions', sortable: false, width: '80px' },
]

let pollingInterval = null

const formatMarketId = (id) => {
  if (!id) return '-'
  if (id.length > 20) return '...' + id.slice(-16)
  return id
}

const formatSessionId = (id) => {
  if (!id) return '-'
  const parts = id.split('_')
  if (parts.length >= 2) {
    return `${parts[0].slice(-6)}_${parts[1].slice(0, 6)}`
  }
  return id.slice(-12)
}

const getStatusClass = (status) => {
  const classes = {
    pending: 'status-pending',
    active: 'status-active',
    completed: 'status-completed',
  }
  return classes[status] || ''
}

const fetchActiveSessions = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}sessions`)
    activeSessions.value = response.data || []

    runningSessions.value = runningSessions.value.filter(s =>
      activeSessions.value.some(a => a.market_id?.includes(s))
    )
  } catch (error) {
    console.error('Failed to fetch sessions:', error)
  }
}

const forceStartSession = async (marketId) => {
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}sessions/${marketId}/force-start`)
    uiStore.showSuccess('Session started')
    await fetchActiveSessions()
  } catch (error) {
    uiStore.showError(error.response?.data?.detail || 'Error starting session')
  }
}

const startHeadlessBatch = async () => {
  startingBatch.value = true
  try {
    const params = new URLSearchParams({
      num_markets: batchConfig.value.numMarkets,
      start_treatment: batchConfig.value.startTreatment,
      parallel: batchConfig.value.parallel,
      delay_seconds: batchConfig.value.delaySeconds,
    })

    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/run_headless_batch?${params}`)

    if (response.data.session_id) {
      runningSessions.value.push(response.data.session_id)
      uiStore.showSuccess(`Started batch: ${formatSessionId(response.data.session_id)}`)
    }

    await fetchActiveSessions()
  } catch (error) {
    uiStore.showError(error.response?.data?.detail || 'Failed to start batch')
  } finally {
    startingBatch.value = false
  }
}

onMounted(() => {
  fetchActiveSessions()
  pollingInterval = setInterval(fetchActiveSessions, 5000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})
</script>

<style scoped>
.markets-tab {
  max-width: 900px;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

/* ===== Section Layout (shared with ConfigTab) ===== */
.config-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.section-header-line {
  width: 3px;
  height: 18px;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--tracking-tight);
}

/* ===== Market Count Badge ===== */
.market-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  font-family: var(--font-mono);
  background: var(--color-bg-elevated);
  color: var(--color-text-muted);
  border: var(--border-width) solid var(--color-border);
}

.market-count-live {
  background: var(--color-success-light);
  color: var(--color-success);
  border-color: rgba(22, 163, 74, 0.25);
}

/* ===== Config Card (shared pattern) ===== */
.config-card {
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow var(--transition-base);
}

.config-card:hover {
  box-shadow: var(--shadow-sm);
}

.config-card-header {
  padding: var(--space-2) var(--space-3);
  border-bottom: var(--border-width) solid var(--color-border-light);
  background: var(--color-bg-elevated);
}

.config-card-tag {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
}

.config-card-body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.helper-text {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
  line-height: var(--leading-relaxed);
}

/* ===== Empty State ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6) 0;
}

.empty-state-icon {
  font-size: var(--text-3xl);
  color: var(--color-text-muted);
  opacity: 0.4;
}

.empty-state-text {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* ===== Markets Table ===== */
.markets-table-wrap {
  padding: var(--space-2);
}

.market-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: var(--tracking-wide);
}

.member-count {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

/* ===== Status Pill ===== */
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-0-5) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  letter-spacing: var(--tracking-wide);
  text-transform: capitalize;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
}

.status-pending {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.status-pending .status-dot {
  background: var(--color-warning);
}

.status-active {
  background: var(--color-success-light);
  color: var(--color-success);
}

.status-active .status-dot {
  background: var(--color-success);
  animation: pulse-dot 2s ease-in-out infinite;
}

.status-completed {
  background: var(--color-bg-elevated);
  color: var(--color-text-muted);
}

.status-completed .status-dot {
  background: var(--color-text-muted);
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ===== Batch Controls ===== */
.batch-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.batch-options {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.batch-start-btn {
  width: 100%;
}

/* ===== Session Groups ===== */
.sessions-group {
  padding-top: var(--space-3);
  border-top: var(--border-width) solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.sessions-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.sessions-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5);
}

.session-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  font-family: var(--font-mono);
  border-radius: var(--radius-md);
  border: var(--border-width) solid transparent;
  letter-spacing: var(--tracking-wide);
}

.session-chip-running {
  background: var(--color-info-light);
  color: var(--color-info);
  border-color: rgba(37, 99, 235, 0.15);
}

.session-chip-running .session-chip-dot {
  width: 5px;
  height: 5px;
  border-radius: var(--radius-full);
  background: var(--color-info);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.session-chip-done {
  background: var(--color-success-light);
  color: var(--color-success);
  border-color: rgba(22, 163, 74, 0.15);
}

/* ===== Responsive ===== */
@media (max-width: 600px) {
  .batch-controls {
    grid-template-columns: 1fr;
  }

  .batch-options {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
