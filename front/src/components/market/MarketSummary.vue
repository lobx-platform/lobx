<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="10" md="8" lg="6">
        <div class="summary-card">
          <div class="summary-header">Market Summary</div>
          <div class="summary-body">
            <!-- Your Statistics -->
            <div v-if="traderSpecificMetrics" class="stat-section">
              <div class="section-label">Your Statistics</div>
              <div class="stat-row">
                <span class="stat-name">Your Trades</span>
                <span class="stat-val">{{
                  formatValue(traderSpecificMetrics.Trades, 'number')
                }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-name">Inventory Imbalance</span>
                <span class="stat-val">{{
                  formatValue(traderSpecificMetrics.Remaining_Trades, 'number')
                }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-name">PnL</span>
                <span class="stat-val">{{
                  formatValue(traderSpecificMetrics.PnL, 'number')
                }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-name">Market Reward (if selected)</span>
                <span class="stat-val">{{
                  formatValue(traderSpecificMetrics.Reward, 'gbp')
                }}</span>
              </div>
            </div>

            <div class="stat-section">
              <div class="section-label">Market Progress</div>
              <div class="stat-row">
                <span class="stat-name">Current Market</span>
                <span class="stat-val">{{ currentMarket }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-name">Maximum Markets</span>
                <span class="stat-val">{{ maxMarketsDisplay }}</span>
              </div>
            </div>
          </div>

          <!-- Per-market questions (shown after every market) -->
          <div
            v-if="traderSpecificMetrics && !questionnaireCompleted"
            class="questionnaire-section"
          >
            <div class="section-label">Answer the following question to continue:</div>
            <p class="q-prompt">Which statement best describes the market?</p>
            <div class="q-container">
              <v-radio-group v-model="perMarketQuestions.marketDescription">
                <v-radio
                  label="An algorithmic trader consistently bought shares."
                  value="algo_bought"
                ></v-radio>
                <v-radio
                  label="An algorithmic trader consistently sold shares."
                  value="algo_sold"
                ></v-radio>
                <v-radio
                  label="There was no algorithmic trader consistently buying or selling shares."
                  value="no_algo"
                ></v-radio>
              </v-radio-group>
            </div>
          </div>

          <div class="summary-actions">
            <template v-if="isLastMarket">
              <div class="final-section">
                <div class="section-label" style="color: var(--color-primary)">
                  Thank you for your participation!
                </div>
                <p class="final-text">
                  You have completed all trading markets.<br />
                  Your market reward is
                  {{ formatValue(traderSpecificMetrics?.Accumulated_Reward, 'gbp') }}. Your
                  participation fee is {{ formatValue(5, 'gbp') }}.
                  <br /><br />
                  Your final payment will be
                  {{
                    formatValue((traderSpecificMetrics?.Accumulated_Reward || 0) + 5, 'gbp')
                  }}.
                </p>

                <!-- Final Questionnaire Section (last market only) -->
                <div v-if="!questionnaireCompleted" class="final-questionnaire">
                  <div class="section-label">
                    Please complete this short questionnaire before finishing
                  </div>

                  <div class="q-container">
                    <p class="q-prompt">
                      1. Was the overall direction of the price movement clear throughout the
                      markets?
                    </p>
                    <v-radio-group v-model="questionnaire.q1" row>
                      <v-radio label="Yes" value="Yes"></v-radio>
                      <v-radio label="No" value="No"></v-radio>
                      <v-radio label="Not sure" value="Not sure"></v-radio>
                    </v-radio-group>
                  </div>

                  <div class="q-container">
                    <p class="q-prompt">
                      2. Which window of the trading platform provided the most useful information
                      for your decisions?
                    </p>
                    <v-radio-group v-model="questionnaire.q2" row>
                      <v-radio
                        label="Order Book Chart (Bar Plot)"
                        value="Order Book Chart"
                      ></v-radio>
                      <v-radio
                        label="Price History Chart (Line Plot)"
                        value="Price History Chart"
                      ></v-radio>
                      <v-radio
                        label="Market Info Card (Market Information)"
                        value="Market Info Card"
                      ></v-radio>
                    </v-radio-group>
                  </div>

                  <div class="q-container">
                    <p class="q-prompt">
                      3. Were you able to effectively monitor your inventory imbalance using
                      information provided by the platform?
                    </p>
                    <v-radio-group v-model="questionnaire.q3" row>
                      <v-radio label="Yes" value="Yes"></v-radio>
                      <v-radio label="No" value="No"></v-radio>
                      <v-radio label="Not sure" value="Not sure"></v-radio>
                    </v-radio-group>
                  </div>

                  <div class="q-container">
                    <p class="q-prompt">
                      4. Was the Average Price of Buy and Sell trades helpful in informing your
                      decisions?
                    </p>
                    <v-radio-group v-model="questionnaire.q4" row>
                      <v-radio label="Yes" value="Yes"></v-radio>
                      <v-radio label="No" value="No"></v-radio>
                      <v-radio label="Not sure" value="Not sure"></v-radio>
                    </v-radio-group>
                  </div>

                  <v-btn
                    color="primary"
                    @click="submitQuestionnaire"
                    :disabled="!isQuestionnaireComplete"
                    class="mt-2"
                  >
                    Submit Questionnaire
                  </v-btn>
                </div>

                <!-- Show this after questionnaire is completed -->
                <div v-if="questionnaireCompleted" class="mt-4">
                  <p v-if="sessionType === 'prolific'" class="final-text">
                    <strong
                      >Please click
                      <a :href="prolificRedirectUrl" target="_blank">here</a> to complete
                      your submission on Prolific.</strong
                    >
                  </p>
                  <p v-else class="final-text">
                    <strong
                      >Thank you for your participation. You may now close this page.</strong
                    >
                  </p>
                  <v-btn color="primary" variant="outlined" @click="downloadMarketMetrics" class="mt-2">
                    Download Metrics
                  </v-btn>
                </div>
              </div>
            </template>
            <template v-else>
              <v-btn
                color="primary"
                @click="goToNextMarket"
                :loading="isNavigating"
                :disabled="!arePerMarketQuestionsComplete"
                class="mr-4"
              >
                Continue to Next Market
              </v-btn>
              <v-btn color="primary" variant="outlined" @click="downloadMarketMetrics">
                Download Metrics
              </v-btn>
            </template>
          </div>
        </div>
      </v-col>
    </v-row>
  </v-container>
  <v-dialog v-model="showDialog" max-width="400">
    <v-card>
      <v-card-title class="headline">{{ dialogTitle }}</v-card-title>
      <v-card-text>{{ dialogMessage }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="closeDialog">OK</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from '@/api/axios'
import { useTraderStore } from '@/store/app'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { storeToRefs } from 'pinia'
import NavigationService from '@/services/navigation'

const traderStore = useTraderStore()
const sessionStore = useSessionStore()
const authStore = useAuthStore()
const { pnl, vwap } = storeToRefs(traderStore)

const traderId = computed(() => sessionStore.traderId || authStore.traderId)

const traderInfo = ref(null)
const orderBookMetrics = ref(null)
const traderSpecificMetrics = ref(null)
const httpUrl = import.meta.env.VITE_HTTP_URL
const prolificRedirectUrl =
  import.meta.env.VITE_PROLIFIC_REDIRECT_URL ||
  'https://app.prolific.com/submissions/complete?cc=C11I8OGE'
const showDialog = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const isNavigating = ref(false)

const perMarketQuestions = ref({
  marketDescription: null,
  imbalanceReason: null,
})

const hasInventoryImbalance = computed(() => {
  const remaining = traderSpecificMetrics.value?.Remaining_Trades
  return remaining !== undefined && remaining !== null && remaining !== 0
})

const arePerMarketQuestionsComplete = computed(() => {
  if (!perMarketQuestions.value.marketDescription) return false
  return true
})

const questionnaireCompleted = ref(false)
const questionnaire = ref({
  q1: null,
  q2: null,
  q3: null,
  q4: null,
})

const isQuestionnaireComplete = computed(() => {
  return (
    arePerMarketQuestionsComplete.value &&
    questionnaire.value.q1 &&
    questionnaire.value.q2 &&
    questionnaire.value.q3 &&
    questionnaire.value.q4
  )
})

async function submitQuestionnaire() {
  try {
    const responses = [
      questionnaire.value.q1,
      questionnaire.value.q2,
      questionnaire.value.q3,
      questionnaire.value.q4,
      perMarketQuestions.value.marketDescription,
      perMarketQuestions.value.imbalanceReason || 'N/A',
    ]

    let traderIdForSubmit = traderId.value

    if (authStore.user?.isProlific) {
      const prolificPID = authStore.user.prolificData.PROLIFIC_PID
      traderIdForSubmit = `HUMAN_${prolificPID}`
    }

    const response = await axios.post(`${httpUrl}save_questionnaire_response`, {
      trader_id: traderIdForSubmit,
      responses: responses,
    })

    if (response.data.status === 'success') {
      questionnaireCompleted.value = true
      NavigationService.completeStudy()
    } else {
      dialogTitle.value = 'Error'
      dialogMessage.value = 'There was an error saving your responses. Please try again.'
      showDialog.value = true
    }
  } catch (error) {
    console.error('Error submitting questionnaire:', error)
    dialogTitle.value = 'Error'
    dialogMessage.value = 'There was an error saving your responses. Please try again.'
    showDialog.value = true
  }
}

const closeDialog = () => {
  showDialog.value = false
}

const downloadMarketMetrics = async () => {
  try {
    const response = await axios.get(`${httpUrl}market_metrics`, {
      params: {
        trader_id: traderId.value,
        market_id: traderId.value,
      },
      responseType: 'blob',
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `trader_${traderId.value}_metrics.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading market metrics:', error)
    dialogTitle.value = 'Error'
    dialogMessage.value = 'Failed to download market metrics. Please try again.'
    showDialog.value = true
  }
}

const maxRetries = 3
const retryDelay = 1000

async function fetchTraderInfo() {
  if (!traderId.value) {
    console.error('No trader ID available')
    return
  }

  try {
    const response = await axios.get(`${httpUrl}trader_info/${traderId.value}`)
    traderInfo.value = response.data.data
    orderBookMetrics.value = response.data.data.order_book_metrics
    traderSpecificMetrics.value = response.data.data.trader_specific_metrics

    if (traderInfo.value && (!orderBookMetrics.value || !traderSpecificMetrics.value)) {
      let retryCount = 0
      const retryMetrics = async () => {
        if (retryCount >= maxRetries) return

        await new Promise((resolve) => setTimeout(resolve, retryDelay))

        try {
          const retryResponse = await axios.get(`${httpUrl}trader_info/${traderId.value}`)
          if (retryResponse.data.data) {
            orderBookMetrics.value = retryResponse.data.data.order_book_metrics
            traderSpecificMetrics.value = retryResponse.data.data.trader_specific_metrics

            if (orderBookMetrics.value && traderSpecificMetrics.value) {
              return
            }
          }
          retryCount++
          await retryMetrics()
        } catch (error) {
          retryCount++
          await retryMetrics()
        }
      }

      retryMetrics()
    }
  } catch (error) {
    console.error('Failed to fetch trader info:', error)
  }
}

const formatValue = (value, format) => {
  if (value === undefined || value === null) {
    return 'N/A'
  }
  if (format === 'currency' && typeof value === 'number') {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
  } else if (format === 'gbp' && typeof value === 'number') {
    return value.toLocaleString('en-GB', { style: 'currency', currency: 'GBP' })
  } else if (format === 'number' && typeof value === 'number') {
    return value.toLocaleString('en-US')
  }
  return value
}

async function savePerMarketResponses() {
  let traderIdForSubmit = traderId.value
  if (authStore.user?.isProlific) {
    const prolificPID = authStore.user.prolificData.PROLIFIC_PID
    traderIdForSubmit = `HUMAN_${prolificPID}`
  }

  await axios.post(`${httpUrl}save_questionnaire_response`, {
    trader_id: traderIdForSubmit,
    responses: [
      perMarketQuestions.value.marketDescription,
      perMarketQuestions.value.imbalanceReason || 'N/A',
    ],
    market_number: currentMarket.value,
  })
}

const goToNextMarket = async () => {
  isNavigating.value = true

  try {
    await savePerMarketResponses().catch((e) => console.warn('Failed to save responses:', e))

    if (!sessionStore.canStartNewMarket) {
      dialogTitle.value = 'Maximum Markets Reached'
      dialogMessage.value = 'You have completed the maximum number of markets allowed.'
      showDialog.value = true
      isNavigating.value = false
      return
    }

    try {
      await NavigationService.startNextMarket()
    } catch (navError) {
      console.warn('NavigationService failed, falling back to reload:', navError)
      window.location.href = window.location.origin + '/onboarding/ready'
    }
  } catch (error) {
    console.error('Error navigating to next market:', error)
    window.location.href = window.location.origin + '/onboarding/ready'
  }
}

const currentMarket = computed(() => {
  return (
    traderInfo.value?.all_attributes?.historical_markets_count ||
    sessionStore.marketsCompleted ||
    1
  )
})

const maxMarketsDisplay = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin || authStore.isAdmin) {
    return '\u221E'
  }
  return (
    traderInfo.value?.all_attributes?.params?.max_markets_per_human ||
    sessionStore.maxMarkets ||
    'Loading...'
  )
})

const sessionType = computed(() => {
  return traderInfo.value?.all_attributes?.params?.session_type || 'prolific'
})

const isLastMarket = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin || authStore.isAdmin) return false
  const currentCount =
    traderInfo.value?.all_attributes?.historical_markets_count ||
    sessionStore.marketsCompleted ||
    1
  const maxMarkets =
    traderInfo.value?.all_attributes?.params?.max_markets_per_human ||
    sessionStore.maxMarkets ||
    4
  return currentCount >= maxMarkets
})

async function checkQuestionnaireStatus() {
  try {
    let tid = traderId.value
    if (authStore.user?.isProlific) {
      tid = `HUMAN_${authStore.user.prolificData.PROLIFIC_PID}`
    }
    if (!tid) return
    const response = await axios.get(`${httpUrl}questionnaire/status`, {
      params: { trader_id: tid },
    })
    if (response.data?.data?.completed) {
      questionnaireCompleted.value = true
    }
  } catch (e) {
    // silently ignore
  }
}

onMounted(() => {
  fetchTraderInfo()
  checkQuestionnaireStatus()
})
</script>

<style scoped>
.summary-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  max-width: 800px;
  width: 100%;
  overflow: hidden;
}

.summary-header {
  background: var(--color-bg-elevated);
  padding: 16px 24px;
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  border-bottom: 1px solid var(--color-border);
}

.summary-body {
  padding: 24px;
}

.stat-section {
  margin-bottom: 20px;
}

.section-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  margin-bottom: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.stat-name {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.stat-val {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.questionnaire-section {
  padding: 24px;
  border-top: 1px solid var(--color-border);
}

.q-prompt {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  font-style: italic;
}

.q-container {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 12px;
}

.summary-actions {
  padding: 24px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.final-section {
  text-align: center;
  width: 100%;
}

.final-text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

.final-text a {
  color: var(--color-primary);
}

.final-questionnaire {
  text-align: left;
  margin-top: 16px;
}
</style>
