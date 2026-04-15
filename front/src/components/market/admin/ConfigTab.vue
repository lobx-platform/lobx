<template>
  <div class="config-tab">

    <!-- ===== SECTION 1: Market Settings ===== -->
    <div class="config-section">
      <div class="section-header">
        <h2 class="section-title">Market Settings</h2>
        <div class="header-actions">
          <v-text-field
            v-model="prolificRedirectUrl"
            label="Prolific Redirect URL"
            hide-details
            density="compact"
            variant="outlined"
            style="min-width: 300px"
            placeholder="https://app.prolific.com/submissions/complete?cc=CODE"
          />
          <button
            class="tp-btn tp-btn-secondary"
            @click="downloadAll"
            :disabled="!serverActive || downloading"
          >
            {{ downloading ? 'Downloading...' : 'Download All' }}
          </button>
          <button
            class="tp-btn tp-btn-secondary"
            @click="resetState"
            :disabled="!serverActive || resettingState"
          >
            {{ resettingState ? 'Resetting...' : 'Reset Experiment' }}
          </button>
          <button
            class="tp-btn tp-btn-primary"
            @click="saveSettings"
            :disabled="!serverActive"
          >
            Save &amp; Apply
          </button>
        </div>
      </div>

      <div class="cards-grid">
        <!-- Order Throttling -->
        <div class="config-card">
          <div class="config-card-header">
            <span class="config-card-tag">Throttling</span>
          </div>
          <div class="config-card-body">
            <table class="plain-table">
              <thead>
                <tr>
                  <th>Trader Type</th>
                  <th>Delay (ms)</th>
                  <th>Max Orders</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="traderType in traderTypes" :key="traderType">
                  <td class="font-mono">{{ formatTraderType(traderType) }}</td>
                  <td>
                    <v-text-field
                      v-model.number="formState.throttle_settings[traderType].order_throttle_ms"
                      type="number"
                      min="0"
                      hide-details
                      density="compact"
                      variant="outlined"
                      @input="updatePersistentSettings"
                    />
                  </td>
                  <td>
                    <v-text-field
                      v-model.number="formState.throttle_settings[traderType].max_orders_per_window"
                      type="number"
                      min="1"
                      hide-details
                      density="compact"
                      variant="outlined"
                      @input="updatePersistentSettings"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Dynamic Parameter Group Cards -->
        <div
          v-for="(group, hint) in groupedFields"
          :key="hint"
          class="config-card"
        >
          <div class="config-card-header">
            <span class="config-card-tag">{{ formatGroupTitle(hint) }}</span>
          </div>
          <div class="config-card-body">
            <div class="param-grid">
              <v-tooltip v-for="field in group" :key="field.name" location="top" :text="field.name">
                <template v-slot:activator="{ props: tooltipProps }">
                  <div class="param-item" v-bind="tooltipProps">
                    <v-switch
                      v-if="field.type === 'boolean'"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      hide-details
                      color="primary"
                      density="compact"
                      :class="getFieldStyle(field.name)"
                      @update:modelValue="updatePersistentSettings"
                    />
                    <v-text-field
                      v-else-if="isArrayField(field)"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      hide-details
                      density="compact"
                      variant="outlined"
                      :class="getFieldStyle(field.name)"
                      @input="handleArrayInput(field.name, $event)"
                    />
                    <v-text-field
                      v-else
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      :type="getFieldType(field)"
                      hide-details
                      density="compact"
                      variant="outlined"
                      :class="getFieldStyle(field.name)"
                      @input="updatePersistentSettings"
                    />
                  </div>
                </template>
              </v-tooltip>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== SECTION 2: Treatment Sequence ===== -->
    <div class="config-section">
      <div class="section-header section-header-toggle" @click="showTreatments = !showTreatments">
        <h2 class="section-title">Treatment Sequence</h2>
        <span class="toggle-indicator">{{ showTreatments ? '\u2212' : '+' }}</span>
      </div>

      <div v-show="showTreatments" class="section-body">
        <div class="config-card">
          <div class="config-card-body">
            <p class="helper-text">
              Define different trader compositions for each market in YAML format.
            </p>

            <v-textarea
              v-model="treatmentYaml"
              label="Treatment YAML"
              rows="10"
              variant="outlined"
              class="yaml-editor"
              :error="yamlError !== ''"
              :error-messages="yamlError"
            />

            <div v-if="treatments.length > 0" class="treatment-list">
              <span
                v-for="(t, i) in treatments"
                :key="i"
                class="treatment-item"
              >
                {{ i }}: {{ t.name || `Treatment ${i}` }}
              </span>
            </div>

            <div class="card-actions">
              <button class="tp-btn tp-btn-secondary" @click="loadTreatments" :disabled="!serverActive">
                Load from Server
              </button>
              <button class="tp-btn tp-btn-primary" @click="saveTreatments" :disabled="!serverActive">
                Save Treatments
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from '@/api/axios'
import { debounce } from 'lodash'
import { useUIStore } from '@/store/ui'
import Haikunator from 'haikunator'

const props = defineProps({
  formState: { type: Object, required: true },
  formFields: { type: Array, required: true },
  serverActive: { type: Boolean, required: true },
})

const emit = defineEmits(['update:formState'])

const uiStore = useUIStore()

// Treatment state
const showTreatments = ref(false)
const treatmentYaml = ref('')
const treatments = ref([])
const yamlError = ref('')

// Prolific redirect URL
const prolificRedirectUrl = ref('')
const generatingCredentials = ref(false)
const savingProlific = ref(false)
const resettingState = ref(false)
const downloading = ref(false)


const traderTypes = computed(() => Object.keys(props.formState.throttle_settings || {}))

const formatTraderType = (type) => {
  return type.replace('_', ' ').toLowerCase().split(' ').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ').substring(0, 12)
}

const formatGroupTitle = (hint) => {
  const titleMap = {
    'model_parameter': 'Model Parameters',
    'noise_parameter': 'Noise Traders',
    'informed_parameter': 'Informed Traders',
    'human_parameter': 'Human Traders',
  }
  return titleMap[hint] || hint.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const groupedFields = computed(() => {
  const groups = {}
  const filteredFields = props.formFields.filter(field => field.name !== 'throttle_settings')
  filteredFields.forEach((field) => {
    const hint = field.hint || 'other'
    if (!groups[hint]) groups[hint] = []
    groups[hint].push(field)
  })
  return groups
})

const getFieldType = (field) => {
  if (!field || !field.type) return 'text'
  return ['number', 'integer'].includes(field.type) ? 'number' : 'text'
}

const isArrayField = (field) => field.type === 'array'

const handleArrayInput = (fieldName, event) => {
  const value = typeof event === 'object' && event?.target ? event.target.value : String(event ?? '')
  if (fieldName === 'predefined_goals') {
    props.formState[fieldName] = value === '' ? [] : value.split(',').map((v) => parseInt(v.trim())).filter((n) => !isNaN(n))
  } else {
    props.formState[fieldName] = value === '' ? [] : value.split(',').map((item) => item.trim())
  }
  updatePersistentSettings()
}

const getFieldStyle = (fieldName) => {
  const defaultValue = props.formFields.find((f) => f.name === fieldName)?.default
  const currentValue = props.formState[fieldName]
  const isDifferent = (() => {
    if (Array.isArray(defaultValue) || Array.isArray(currentValue)) {
      return JSON.stringify(defaultValue) !== JSON.stringify(currentValue)
    }
    if (typeof defaultValue === 'number' || typeof currentValue === 'number') {
      return Number(defaultValue) !== Number(currentValue)
    }
    return defaultValue !== currentValue
  })()
  return isDifferent ? 'field-modified' : ''
}

const debouncedUpdate = debounce(async (settings) => {
  try {
    const cleanSettings = { ...settings }
    if (cleanSettings.throttle_settings) {
      Object.entries(cleanSettings.throttle_settings).forEach(([trader, config]) => {
        cleanSettings.throttle_settings[trader] = {
          order_throttle_ms: parseInt(config.order_throttle_ms) || 0,
          max_orders_per_window: parseInt(config.max_orders_per_window) || 1,
        }
      })
    }
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_base_settings`, { settings: cleanSettings })
  } catch (error) {
    console.error('Failed to update settings:', error)
  }
}, 500)

const updatePersistentSettings = () => {
  emit('update:formState', props.formState)
  debouncedUpdate(props.formState)
}

const saveSettings = async () => {
  try {
    updatePersistentSettings()
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/reset_state`)
    uiStore.showSuccess('Settings saved')
  } catch (error) {
    console.error('Error saving settings:', error)
    uiStore.showError('Failed to save settings')
  }
}

const resetState = async () => {
  resettingState.value = true
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/reset_state`)
    uiStore.showSuccess('Experiment state reset — all sessions, markets, and rewards cleared')
  } catch (error) {
    console.error('Error resetting state:', error)
    uiStore.showError('Failed to reset state')
  } finally {
    resettingState.value = false
  }
}

// Treatment functions
const loadTreatments = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_treatments`)
    treatmentYaml.value = response.data.yaml_content || ''
    treatments.value = response.data.treatments || []
    yamlError.value = ''
  } catch (error) {
    yamlError.value = 'Failed to load treatments'
  }
}

const saveTreatments = async () => {
  try {
    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_treatments`, { yaml_content: treatmentYaml.value })
    treatments.value = response.data.treatments || []
    yamlError.value = ''
    uiStore.showSuccess('Treatments saved')
  } catch (error) {
    yamlError.value = error.response?.data?.detail || 'Failed to save'
  }
}

const downloadAll = async () => {
  downloading.value = true
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/download-all`, {
      responseType: 'blob',
    })
    const disposition = response.headers['content-disposition'] || ''
    const match = disposition.match(/filename=(.+)/)
    const filename = match ? match[1] : 'experiment_data.zip'
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    uiStore.showSuccess('Download started')
  } catch (error) {
    console.error('Download failed:', error)
    uiStore.showError('Failed to download data')
  } finally {
    downloading.value = false
  }
}

onMounted(() => {
  if (props.serverActive) {
    loadTreatments()
  }
})

watch(() => props.serverActive, (newVal) => {
  if (newVal) {
    loadTreatments()
  }
})
</script>

<style scoped>
.config-tab {
  max-width: 1200px;
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

.section-header-toggle {
  cursor: pointer;
  user-select: none;
}

.section-header-toggle:hover .section-title {
  color: var(--color-text-secondary);
}

.section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--tracking-tight);
}

.header-actions {
  display: flex;
  gap: var(--space-2);
  margin-left: auto;
}

.section-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.toggle-indicator {
  margin-left: auto;
  font-size: var(--text-lg);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  line-height: 1;
}

/* ===== Cards Grid ===== */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-4);
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
  padding: var(--space-1-5) var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: middle;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.plain-table tr:last-child td {
  border-bottom: none;
}

.font-mono {
  font-family: var(--font-mono);
}

/* ===== Parameter Grid ===== */
.param-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.param-item {
  min-width: 0;
}

/* ===== Modified Field Indicator ===== */
.field-modified :deep(.v-field) {
  border-color: var(--color-warning) !important;
}

.field-modified :deep(.v-label) {
  color: var(--color-warning) !important;
}

/* ===== Card Actions ===== */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}

/* ===== Helper Text ===== */
.helper-text {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
  line-height: var(--leading-relaxed);
}

/* ===== YAML Editor ===== */
.yaml-editor :deep(textarea) {
  font-family: var(--font-mono) !important;
  font-size: var(--text-xs) !important;
  line-height: 1.6 !important;
}

/* ===== Credentials ===== */
.credentials-field :deep(textarea) {
  font-family: var(--font-mono) !important;
  font-size: var(--text-xs) !important;
}

/* ===== Treatment List ===== */
.treatment-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.treatment-item {
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
}

/* ===== Form Rows ===== */
.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.form-row-inline {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* ===== Overrides Section ===== */
.overrides-section {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.overrides-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

/* ===== Links Output ===== */
.links-output {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.links-textarea :deep(textarea) {
  font-family: var(--font-mono) !important;
  font-size: var(--text-xs) !important;
}

/* ===== Responsive ===== */
@media (max-width: 700px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }

  .param-grid {
    grid-template-columns: 1fr;
  }

  .form-row-2 {
    grid-template-columns: 1fr;
  }
}
</style>
