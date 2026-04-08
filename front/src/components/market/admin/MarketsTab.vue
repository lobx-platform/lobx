<template>
  <div class="markets-tab">

    <!-- ===== Active Markets ===== -->
    <div class="config-section">
      <div class="section-header">
        <h2 class="section-title">Active Markets</h2>
        <span class="market-count">{{ activeSessions.length }}</span>
      </div>

      <div class="config-card">
        <div class="config-card-body" v-if="activeSessions.length === 0">
          <p class="empty-text">No active markets</p>
        </div>
        <div v-else class="config-card-body">
          <table class="plain-table">
            <thead>
              <tr>
                <th>Market ID</th>
                <th>Status</th>
                <th>Members</th>
                <th style="width: 80px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in activeSessions" :key="item.market_id">
                <td class="font-mono">{{ formatMarketId(item.market_id) }}</td>
                <td>{{ item.status }}</td>
                <td class="font-mono">{{ item.member_ids?.length || 0 }}</td>
                <td>
                  <button
                    class="tp-btn tp-btn-sm tp-btn-secondary"
                    :disabled="item.status === 'active' || !item.member_ids?.length"
                    @click="forceStartSession(item.market_id)"
                  >
                    Start
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ===== AI-Only Market Runner ===== -->
    <div class="config-section">
      <div class="section-header">
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
            class="tp-btn tp-btn-primary"
            @click="startHeadlessBatch"
            :disabled="!serverActive || startingBatch"
            style="width: 100%"
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
                class="session-id"
              >
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
                class="session-id session-id-done"
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

/* ===== Section Layout ===== */
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

.section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--tracking-tight);
}

/* ===== Market Count ===== */
.market-count {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--color-text-muted);
}

/* ===== Config Card ===== */
.config-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.config-card-header {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
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
.empty-text {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-align: center;
  padding: var(--space-4) 0;
  margin: 0;
}

/* ===== Plain Table ===== */
.plain-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.plain-table th {
  text-align: left;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  padding: var(--space-1) var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.plain-table td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: middle;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.plain-table tr:last-child td {
  border-bottom: none;
}

.font-mono {
  font-family: var(--font-mono);
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

/* ===== Session Groups ===== */
.sessions-group {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
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
  gap: var(--space-2);
}

.session-id {
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  letter-spacing: var(--tracking-wide);
}

.session-id-done {
  color: var(--color-text-muted);
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
