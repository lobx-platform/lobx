<template>
  <div class="config-tab">
    <!-- Market Configuration -->
    <section class="tp-card mb-4">
      <header class="tp-card-header">
        <h2 class="tp-card-title">Market Configuration</h2>
      </header>

      <div class="tp-card-body">
        <div class="parameter-grid">
          <!-- Order Throttling Settings -->
          <div class="tp-card parameter-card">
            <header class="tp-card-header">
              <h3 class="tp-card-title text-sm">Order Throttling</h3>
            </header>
            <div class="tp-card-body">
              <div class="throttle-grid">
                <template v-for="traderType in traderTypes" :key="traderType">
                  <div class="throttle-row">
                    <span class="tp-label">{{ formatTraderType(traderType) }}</span>
                    <div class="throttle-inputs">
                      <v-text-field
                        v-model.number="formState.throttle_settings[traderType].order_throttle_ms"
                        label="ms"
                        type="number"
                        min="0"
                        hide-details
                        @input="updatePersistentSettings"
                      />
                      <v-text-field
                        v-model.number="formState.throttle_settings[traderType].max_orders_per_window"
                        label="Max"
                        type="number"
                        min="1"
                        hide-details
                        @input="updatePersistentSettings"
                      />
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Regular Parameter Groups -->
          <div
            v-for="(group, hint) in groupedFields"
            :key="hint"
            class="tp-card parameter-card"
          >
            <header class="tp-card-header">
              <h3 class="tp-card-title text-sm">{{ formatGroupTitle(hint) }}</h3>
            </header>
            <div class="tp-card-body">
              <div class="field-grid">
                <v-tooltip v-for="field in group" :key="field.name" location="top" :text="field.name">
                <template v-slot:activator="{ props: tooltipProps }">
                  <div class="field-item" v-bind="tooltipProps">
                    <!-- Boolean switch -->
                    <v-switch
                      v-if="field.type === 'boolean'"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      hide-details
                      color="primary"
                      :class="getFieldStyle(field.name)"
                      @update:modelValue="updatePersistentSettings"
                    />
                    <!-- Array fields -->
                    <v-text-field
                      v-else-if="isArrayField(field)"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      hide-details
                      :class="getFieldStyle(field.name)"
                      @input="handleArrayInput(field.name, $event)"
                    />
                    <!-- Regular fields -->
                    <v-text-field
                      v-else
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      :type="getFieldType(field)"
                      hide-details
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

      <footer class="tp-card-footer">
        <button
          class="tp-btn tp-btn-primary"
          @click="saveSettings"
          :disabled="!serverActive"
        >
          Save Settings
        </button>
      </footer>
    </section>

    <!-- Treatment Sequence -->
    <section class="tp-card mb-4">
      <header 
        class="tp-card-header tp-card-header-collapsible"
        @click="showTreatments = !showTreatments"
      >
        <h2 class="tp-card-title">Treatment Sequence</h2>
        <v-icon size="20">{{ showTreatments ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </header>

      <v-expand-transition>
        <div v-show="showTreatments">
          <div class="tp-card-body">
            <p class="text-sm text-secondary mb-3">
              Define different trader compositions for each market.
            </p>
            
            <v-textarea
              v-model="treatmentYaml"
              label="Treatment YAML"
              rows="10"
              class="yaml-editor"
              :error="yamlError !== ''"
              :error-messages="yamlError"
            />

            <div v-if="treatments.length > 0" class="treatment-chips">
              <span
                v-for="(t, i) in treatments"
                :key="i"
                class="tp-badge"
              >
                {{ i }}: {{ t.name || `Treatment ${i}` }}
              </span>
            </div>
          </div>

          <footer class="tp-card-footer">
            <button class="tp-btn tp-btn-secondary" @click="loadTreatments" :disabled="!serverActive">
              Load
            </button>
            <button class="tp-btn tp-btn-primary" @click="saveTreatments" :disabled="!serverActive">
              Save
            </button>
          </footer>
        </div>
      </v-expand-transition>
    </section>

    <!-- Session & Prolific Settings (Collapsed) -->
    <section class="tp-card">
      <header
        class="tp-card-header tp-card-header-collapsible"
        @click="showProlific = !showProlific"
      >
        <h2 class="tp-card-title">Session & Prolific Settings</h2>
        <v-icon size="20">{{ showProlific ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </header>

      <v-expand-transition>
        <div v-show="showProlific">
          <div class="tp-card-body">
            <v-select
              v-model="formState.session_type"
              :items="['prolific', 'lab']"
              label="Session Type"
              hide-details
              class="mb-3"
              @update:model-value="updatePersistentSettings"
            />

            <v-textarea
              v-model="prolificSettings.credentials"
              label="Prolific Credentials"
              hide-details
              class="mb-3"
              placeholder="username1,password1&#10;username2,password2"
              rows="3"
            />

            <div class="credential-gen mb-3">
              <v-text-field
                v-model="numCredentials"
                label="Count"
                type="number"
                min="1"
                max="20"
                hide-details
                style="max-width: 100px"
              />
              <button class="tp-btn tp-btn-secondary" @click="generateCredentials" :disabled="generatingCredentials">
                Generate
              </button>
            </div>

            <v-text-field
              v-model="prolificSettings.studyId"
              label="Study ID"
              hide-details
              class="mb-3"
            />

            <v-text-field
              v-model="prolificSettings.redirectUrl"
              label="Redirect URL"
              hide-details
            />
          </div>

          <footer class="tp-card-footer">
            <button
              class="tp-btn tp-btn-primary"
              @click="saveProlificSettings"
              :disabled="savingProlific"
              style="width: 100%"
            >
              Save Prolific Settings
            </button>
          </footer>

          <!-- Lab Links Generation (only in lab mode) -->
          <div v-if="formState.session_type === 'lab'" class="tp-card-body" style="border-top: 1px solid var(--color-border, #e0e0e0)">
            <h3 class="text-subtitle-1 font-weight-medium mb-2">Lab Session Links</h3>
            <div class="credential-gen mb-3">
              <v-text-field
                v-model="numLabLinks"
                label="Total Participants"
                type="number"
                min="1"
                max="200"
                hide-details
                style="max-width: 150px"
              />
              <v-text-field
                v-model="numTreatments"
                label="Treatments"
                type="number"
                min="1"
                max="8"
                hide-details
                style="max-width: 120px"
              />
              <button class="tp-btn tp-btn-secondary" @click="generateLabLinks" :disabled="generatingLabLinks">
                {{ generatingLabLinks ? 'Generating...' : 'Generate Links' }}
              </button>
            </div>

            <!-- Treatment overrides (when more than 1 treatment) -->
            <div v-if="parseInt(numTreatments) > 1" class="mb-3">
              <h4 class="text-subtitle-2 font-weight-medium mb-2">Treatment Parameter Overrides</h4>
              <div v-for="t in parseInt(numTreatments)" :key="t" class="mb-2" style="display: flex; gap: 8px; align-items: center">
                <span style="min-width: 30px; font-weight: 500">T{{ t }}:</span>
                <v-text-field
                  v-model="treatmentOverrides[t-1].informed_trade_intensity"
                  label="informed_trade_intensity"
                  type="number"
                  step="0.01"
                  hide-details
                  density="compact"
                  style="max-width: 180px"
                />
                <v-text-field
                  v-model="treatmentOverrides[t-1].informed_share_passive"
                  label="informed_share_passive"
                  type="number"
                  step="0.01"
                  hide-details
                  density="compact"
                  style="max-width: 180px"
                />
              </div>
              <button class="tp-btn tp-btn-secondary" @click="saveTreatmentOverrides" style="width: 100%">
                Save Treatment Overrides
              </button>
            </div>

            <v-textarea
              v-if="labLinks"
              v-model="labLinks"
              label="Lab Links (one per line)"
              readonly
              rows="5"
              hide-details
              class="mb-3"
            />
            <button v-if="labLinks" class="tp-btn tp-btn-secondary" @click="copyLabLinks" style="width: 100%">
              Copy Links
            </button>
          </div>
        </div>
      </v-expand-transition>
    </section>
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
    fetchProlificSettings()
  }
})

watch(() => props.serverActive, (newVal) => {
  if (newVal) {
    loadTreatments()
    fetchProlificSettings()
  }
})
</script>

<style scoped>
.config-tab {
  max-width: 1200px;
}

.mb-3 {
  margin-bottom: var(--space-3);
}

.mb-4 {
  margin-bottom: var(--space-4);
}

/* Parameter Grid */
.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-3);
}

.parameter-card {
  height: fit-content;
}

/* Throttle Grid */
.throttle-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.throttle-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.throttle-row .tp-label {
  min-width: 90px;
  margin-bottom: 0;
}

.throttle-inputs {
  display: flex;
  gap: var(--space-2);
  flex: 1;
}

.throttle-inputs .v-text-field {
  flex: 1;
}

/* Field Grid */
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.field-item {
  min-width: 0;
}

/* Modified field indicator */
.field-modified :deep(.v-field) {
  border-color: var(--color-warning) !important;
}

.field-modified :deep(.v-label) {
  color: var(--color-warning) !important;
}

/* Treatment chips */
.treatment-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-3);
}

/* YAML Editor */
.yaml-editor :deep(textarea) {
  font-family: var(--font-mono) !important;
  font-size: var(--text-xs) !important;
}

/* Credential generator */
.credential-gen {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
