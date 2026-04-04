<template>
  <div class="config-tab">

    <!-- ===== SECTION 1: Market Settings ===== -->
    <div class="config-section">
      <div class="section-header">
        <div class="section-header-line"></div>
        <h2 class="section-title">Market Settings</h2>
        <div class="section-header-actions">
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
        <!-- Order Throttling Card -->
        <div class="config-card">
          <div class="config-card-header">
            <span class="config-card-tag">Throttling</span>
          </div>
          <div class="config-card-body">
            <div class="throttle-table">
              <div class="throttle-table-head">
                <span class="throttle-col-label">Trader Type</span>
                <span class="throttle-col-value">Delay (ms)</span>
                <span class="throttle-col-value">Max Orders</span>
              </div>
              <template v-for="traderType in traderTypes" :key="traderType">
                <div class="throttle-table-row">
                  <span class="throttle-col-label font-mono">{{ formatTraderType(traderType) }}</span>
                  <div class="throttle-col-value">
                    <v-text-field
                      v-model.number="formState.throttle_settings[traderType].order_throttle_ms"
                      type="number"
                      min="0"
                      hide-details
                      density="compact"
                      variant="outlined"
                      @input="updatePersistentSettings"
                    />
                  </div>
                  <div class="throttle-col-value">
                    <v-text-field
                      v-model.number="formState.throttle_settings[traderType].max_orders_per_window"
                      type="number"
                      min="1"
                      hide-details
                      density="compact"
                      variant="outlined"
                      @input="updatePersistentSettings"
                    />
                  </div>
                </div>
              </template>
            </div>
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
        <div class="section-header-line"></div>
        <h2 class="section-title">Treatment Sequence</h2>
        <v-icon size="18" class="toggle-chevron" :class="{ 'toggle-open': showTreatments }">mdi-chevron-down</v-icon>
      </div>

      <v-expand-transition>
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

              <div v-if="treatments.length > 0" class="treatment-tags">
                <span
                  v-for="(t, i) in treatments"
                  :key="i"
                  class="treatment-tag"
                >
                  <span class="treatment-tag-index">{{ i }}</span>
                  {{ t.name || `Treatment ${i}` }}
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
      </v-expand-transition>
    </div>

    <!-- ===== SECTION 3: Session & Lab Settings ===== -->
    <div class="config-section">
      <div class="section-header section-header-toggle" @click="showProlific = !showProlific">
        <div class="section-header-line"></div>
        <h2 class="section-title">Session &amp; Lab Settings</h2>
        <v-icon size="18" class="toggle-chevron" :class="{ 'toggle-open': showProlific }">mdi-chevron-down</v-icon>
      </div>

      <v-expand-transition>
        <div v-show="showProlific" class="section-body">

          <!-- Session Type + Credentials -->
          <div class="config-card">
            <div class="config-card-header">
              <span class="config-card-tag">Credentials &amp; Session</span>
            </div>
            <div class="config-card-body">
              <div class="form-row-2">
                <v-select
                  v-model="formState.session_type"
                  :items="['prolific', 'lab']"
                  label="Session Type"
                  hide-details
                  density="compact"
                  variant="outlined"
                  @update:model-value="updatePersistentSettings"
                />
                <v-text-field
                  v-model="prolificSettings.studyId"
                  label="Study ID"
                  hide-details
                  density="compact"
                  variant="outlined"
                />
              </div>

              <v-textarea
                v-model="prolificSettings.credentials"
                label="Participant Credentials"
                hide-details
                variant="outlined"
                placeholder="username1,password1&#10;username2,password2"
                rows="3"
                class="credentials-field"
              />

              <div class="form-row-inline">
                <v-text-field
                  v-model="numCredentials"
                  label="Count"
                  type="number"
                  min="1"
                  max="20"
                  hide-details
                  density="compact"
                  variant="outlined"
                  style="max-width: 100px"
                />
                <button class="tp-btn tp-btn-secondary" @click="generateCredentials" :disabled="generatingCredentials">
                  Generate Credentials
                </button>
              </div>

              <v-text-field
                v-model="prolificSettings.redirectUrl"
                label="Redirect URL"
                hide-details
                density="compact"
                variant="outlined"
              />

              <div class="card-actions">
                <button
                  class="tp-btn tp-btn-primary tp-btn-lg"
                  @click="saveProlificSettings"
                  :disabled="savingProlific"
                  style="width: 100%"
                >
                  Save Session Settings
                </button>
              </div>
            </div>
          </div>

          <!-- Lab Link Generation (prominent) -->
          <div v-if="formState.session_type === 'lab'" class="config-card config-card-accent">
            <div class="config-card-header">
              <span class="config-card-tag config-card-tag-accent">Lab Link Generator</span>
            </div>
            <div class="config-card-body">
              <div class="form-row-inline">
                <v-text-field
                  v-model="numLabLinks"
                  label="Total Participants"
                  type="number"
                  min="1"
                  max="200"
                  hide-details
                  density="compact"
                  variant="outlined"
                  style="max-width: 160px"
                />
                <v-text-field
                  v-model="numTreatments"
                  label="Treatments"
                  type="number"
                  min="1"
                  max="8"
                  hide-details
                  density="compact"
                  variant="outlined"
                  style="max-width: 120px"
                />
                <button class="tp-btn tp-btn-primary" @click="generateLabLinks" :disabled="generatingLabLinks">
                  {{ generatingLabLinks ? 'Generating...' : 'Generate Links' }}
                </button>
              </div>

              <!-- Treatment Overrides -->
              <div v-if="parseInt(numTreatments) > 1" class="overrides-section">
                <span class="overrides-label">Treatment Parameter Overrides</span>
                <div class="overrides-grid">
                  <div v-for="t in parseInt(numTreatments)" :key="t" class="override-row">
                    <span class="override-tag">T{{ t }}</span>
                    <v-text-field
                      v-model="treatmentOverrides[t-1].informed_trade_intensity"
                      label="informed_trade_intensity"
                      type="number"
                      step="0.01"
                      hide-details
                      density="compact"
                      variant="outlined"
                    />
                    <v-text-field
                      v-model="treatmentOverrides[t-1].informed_share_passive"
                      label="informed_share_passive"
                      type="number"
                      step="0.01"
                      hide-details
                      density="compact"
                      variant="outlined"
                    />
                  </div>
                </div>
                <button class="tp-btn tp-btn-secondary" @click="saveTreatmentOverrides" style="width: 100%">
                  Save Treatment Overrides
                </button>
              </div>

              <!-- Generated Links Output -->
              <div v-if="labLinks" class="links-output">
                <v-textarea
                  v-model="labLinks"
                  label="Generated Lab Links"
                  readonly
                  rows="5"
                  hide-details
                  variant="outlined"
                  class="links-textarea"
                />
                <button class="tp-btn tp-btn-primary" @click="copyLabLinks" style="width: 100%">
                  Copy All Links to Clipboard
                </button>
              </div>
            </div>
          </div>

        </div>
      </v-expand-transition>
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
const haikunator = new Haikunator()

// Treatment state
const showTreatments = ref(false)
const treatmentYaml = ref('')
const treatments = ref([])
const yamlError = ref('')
// Prolific state
const showProlific = ref(false)
const prolificSettings = ref({ credentials: '', studyId: '', redirectUrl: '' })
const numCredentials = ref(5)
const generatingCredentials = ref(false)
const savingProlific = ref(false)

// Lab links state
const numLabLinks = ref(100)
const numTreatments = ref(4)
const labLinks = ref('')
const generatingLabLinks = ref(false)
// Pre-fill with Alessio's T1-T4 defaults
const treatmentOverrides = ref([
  { informed_trade_intensity: 0.36, informed_share_passive: '' },
  { informed_trade_intensity: 0.69, informed_share_passive: '' },
  { informed_trade_intensity: 0.36, informed_share_passive: 0.4 },
  { informed_trade_intensity: 0.69, informed_share_passive: 0.1 },
  { informed_trade_intensity: '', informed_share_passive: '' },
  { informed_trade_intensity: '', informed_share_passive: '' },
  { informed_trade_intensity: '', informed_share_passive: '' },
  { informed_trade_intensity: '', informed_share_passive: '' },
])

const traderTypes = ['HUMAN', 'NOISE', 'INFORMED', 'MARKET_MAKER', 'INITIAL_ORDER_BOOK']

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

// Prolific functions
const fetchProlificSettings = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`)
    if (response.data?.data) {
      prolificSettings.value = {
        credentials: response.data.data.PROLIFIC_CREDENTIALS || '',
        studyId: response.data.data.PROLIFIC_STUDY_ID || '',
        redirectUrl: response.data.data.PROLIFIC_REDIRECT_URL || '',
      }
    }
  } catch (error) {
    console.error('Failed to fetch Prolific settings:', error)
  }
}

const saveProlificSettings = async () => {
  try {
    savingProlific.value = true
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`, {
      settings: {
        PROLIFIC_CREDENTIALS: prolificSettings.value.credentials,
        PROLIFIC_STUDY_ID: prolificSettings.value.studyId,
        PROLIFIC_REDIRECT_URL: prolificSettings.value.redirectUrl,
      },
    })
    uiStore.showSuccess('Prolific settings saved')
  } catch (error) {
    uiStore.showError('Failed to save Prolific settings')
  } finally {
    savingProlific.value = false
  }
}

const generateCredentials = () => {
  generatingCredentials.value = true
  try {
    const count = parseInt(numCredentials.value) || 5
    const generated = []
    for (let i = 0; i < count; i++) {
      const username = haikunator.haikunate({ tokenLength: 0, delimiter: '' })
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
      let password = ''
      for (let j = 0; j < 10; j++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length))
      }
      generated.push(`${username},${password}`)
    }
    prolificSettings.value.credentials = generated.join('\n')
    uiStore.showSuccess(`Generated ${count} credentials`)
  } finally {
    generatingCredentials.value = false
  }
}

// Lab link functions
const generateLabLinks = async () => {
  generatingLabLinks.value = true
  try {
    const nt = parseInt(numTreatments.value) || 1
    const payload = {
      count: parseInt(numLabLinks.value) || 10,
      num_treatments: nt,
    }
    // Include treatment overrides if using multiple treatments
    if (nt > 1) {
      const overrides = {}
      for (let i = 0; i < nt; i++) {
        const o = {}
        const t = treatmentOverrides.value[i]
        if (t.informed_trade_intensity !== '') o.informed_trade_intensity = parseFloat(t.informed_trade_intensity)
        if (t.informed_share_passive !== '') o.informed_share_passive = parseFloat(t.informed_share_passive)
        if (Object.keys(o).length > 0) overrides[i] = o
      }
      if (Object.keys(overrides).length > 0) payload.treatment_overrides = overrides
    }
    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/generate-lab-links`, payload)
    labLinks.value = (response.data.data?.links || []).join('\n')
    uiStore.showSuccess(`Generated ${numLabLinks.value} lab links (${nt} treatments)`)
  } catch (error) {
    uiStore.showError('Failed to generate lab links')
  } finally {
    generatingLabLinks.value = false
  }
}

const saveTreatmentOverrides = async () => {
  try {
    const nt = parseInt(numTreatments.value) || 1
    const overrides = {}
    for (let i = 0; i < nt; i++) {
      const o = {}
      const t = treatmentOverrides.value[i]
      if (t.informed_trade_intensity !== '') o.informed_trade_intensity = parseFloat(t.informed_trade_intensity)
      if (t.informed_share_passive !== '') o.informed_share_passive = parseFloat(t.informed_share_passive)
      if (Object.keys(o).length > 0) overrides[i] = o
    }
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/treatment-overrides`, { overrides })
    uiStore.showSuccess('Treatment overrides saved')
  } catch (error) {
    uiStore.showError('Failed to save treatment overrides')
  }
}

const copyLabLinks = () => {
  navigator.clipboard.writeText(labLinks.value)
  uiStore.showSuccess('Links copied to clipboard')
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
  color: var(--color-primary);
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

.section-header-actions {
  margin-left: auto;
}

.section-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.toggle-chevron {
  margin-left: auto;
  color: var(--color-text-muted);
  transition: transform var(--transition-base);
}

.toggle-chevron.toggle-open {
  transform: rotate(180deg);
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
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow var(--transition-base);
}

.config-card:hover {
  box-shadow: var(--shadow-sm);
}

.config-card-accent {
  border-color: var(--color-primary-muted);
  background: linear-gradient(180deg, rgba(8, 145, 178, 0.02) 0%, var(--color-bg-surface) 100%);
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

.config-card-tag-accent {
  color: var(--color-primary);
}

.config-card-body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* ===== Throttle Table ===== */
.throttle-table {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.throttle-table-head {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-2);
  padding: 0 0 var(--space-1-5) 0;
  border-bottom: var(--border-width) solid var(--color-border-light);
}

.throttle-table-head .throttle-col-label,
.throttle-table-head .throttle-col-value {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.throttle-table-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-1) 0;
}

.throttle-col-label {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
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
  border-top: var(--border-width) solid var(--color-border-light);
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

/* ===== Treatment Tags ===== */
.treatment-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5);
}

.treatment-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
}

.treatment-tag-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: var(--font-bold);
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
  border-top: var(--border-width) solid var(--color-border-light);
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

.overrides-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.override-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.override-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 28px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-md);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  letter-spacing: var(--tracking-wide);
  flex-shrink: 0;
}

/* ===== Links Output ===== */
.links-output {
  padding-top: var(--space-3);
  border-top: var(--border-width) solid var(--color-border-light);
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

  .throttle-table-head,
  .throttle-table-row {
    grid-template-columns: 0.8fr 1fr 1fr;
  }
}
</style>
