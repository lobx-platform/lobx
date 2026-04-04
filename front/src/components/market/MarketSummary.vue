<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="10" md="8" lg="6">
        <v-card elevation="24" class="market-summary-card">
          <v-card-title class="text-h4 font-weight-bold text-center py-6 primary white--text">
            Trading Market Summary
          </v-card-title>
          <v-card-text class="pa-6">
            <v-row>
              <!-- Your Statistics -->
              <v-col cols="12">
                <div v-if="traderSpecificMetrics" class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Your Statistics</h3>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Your Trades:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Trades, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Inventory Imbalance:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Remaining_Trades, 'number') }}</span>
                    </div>
                   <!--<div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Penalty :</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue( (- traderSpecificMetrics.Remaining_Trades * 5) || 0, 'number') }}</span>
                    </div>  -->
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">PnL:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.PnL, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Market Reward (if selected):</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Reward, 'gbp') }}</span>
                    </div>
                </div>
              </v-col>
              <v-col cols="12">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Market Progress</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Current Market:</span>
                    <span class="text-h6 font-weight-bold">{{ currentMarket }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-subtitle-1">Maximum Markets:</span>
                    <span class="text-h6 font-weight-bold">{{ maxMarketsDisplay }}</span>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>

          <!-- Per-market questions (shown after every market) -->
          <div v-if="traderSpecificMetrics && !questionnaireCompleted" class="pa-6 questionnaire-section">
            <h3 class="text-h6 mb-3">Answer the following question to continue:</h3>
            <p class="text-body-2 mb-3 font-italic">
              Which statement best describes the market?<br>
            </p>
            <div class="question-container mb-4">
              <v-radio-group v-model="perMarketQuestions.marketDescription">
                <v-radio label="An algorithmic trader consistently bought shares." value="algo_bought"></v-radio>
                <v-radio label="An algorithmic trader consistently sold shares." value="algo_sold"></v-radio>
                <v-radio label="There was no algorithmic trader consistently buying or selling shares." value="no_algo"></v-radio>
              </v-radio-group>
            </div>

            <!-- Conditional: inventory imbalance question (only when Remaining_Trades != 0) -->
            <!-- <div v-if="hasInventoryImbalance" class="mt-4">
              <h3 class="text-h6 mb-3">Answer the following question to continue:</h3>
              <p class="text-body-2 mb-3">
                Your number of shares at the end of the market must equal your initial number of shares. Because they did not match, a penalty was applied.<br>
                Why did this happen?
              </p>
              <div class="question-container mb-4">
                <v-radio-group v-model="perMarketQuestions.imbalanceReason">
                  <v-radio label="I did not understand that my final number of shares had to equal my initial number of shares." value="did_not_understand"></v-radio>
                  <v-radio label="I did not have enough time to adjust my shares so that my final number matched my initial number." value="not_enough_time"></v-radio>
                  <v-radio label="I lost track of time." value="lost_track_time"></v-radio>
                </v-radio-group>
              </div>
            </div> -->
          </div>

          <v-card-actions class="justify-center pa-6">
            <template v-if="isLastMarket">
              <div class="text-center">
                <h2 class="text-h5 mb-4 primary--text">Thank you for your participation!</h2>
                <p class="text-subtitle-1 mb-4">
                  You have completed all trading markets.<br>
                  Your market reward is {{ formatValue(traderSpecificMetrics?.Accumulated_Reward, 'gbp') }}. Your participation fee is {{ formatValue(5, 'gbp') }}.
                  <br><br>
                  Your final payment will be {{ formatValue((traderSpecificMetrics?.Accumulated_Reward || 0) + 5, 'gbp') }}.
                </p>
                <!-- Final Questionnaire Section (last market only) -->
                <div v-if="!questionnaireCompleted" class="questionnaire-section mt-4 mb-4">
                  <h3 class="text-h6 mb-3">Please complete this short questionnaire before finishing</h3>

                  <!-- Question 1 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">1. Was the overall direction of the price movement clear throughout the markets?</p>
                    <v-radio-group v-model="questionnaire.q1" row>
                      <v-radio label="Yes" value="Yes"></v-radio>
                      <v-radio label="No" value="No"></v-radio>
                      <v-radio label="Not sure" value="Not sure"></v-radio>
                    </v-radio-group>
                  </div>

                  <!-- Question 2 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">2. Which window of the trading platform provided the most useful information for your decisions?</p>
                    <v-radio-group v-model="questionnaire.q2" row>
                      <v-radio label="Order Book Chart (Bar Plot)" value="Order Book Chart"></v-radio>
                      <v-radio label="Price History Chart (Line Plot)" value="Price History Chart"></v-radio>
                      <v-radio label="Market Info Card (Market Information)" value="Market Info Card"></v-radio>
                    </v-radio-group>
                  </div>

                  <!-- Question 3 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">3. Were you able to effectively monitor your inventory imbalance using information provided by the platform?</p>
                    <v-radio-group v-model="questionnaire.q3" row>
                      <v-radio label="Yes" value="Yes"></v-radio>
                      <v-radio label="No" value="No"></v-radio>
                      <v-radio label="Not sure" value="Not sure"></v-radio>
                    </v-radio-group>
                  </div>

                  <!-- Question 4 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">4. Was the Average Price of Buy and Sell trades helpful in informing your decisions?</p>
                    <v-radio-group v-model="questionnaire.q4" row>
                      <v-radio label="Yes" value="Yes"></v-radio>
                      <v-radio label="No" value="No"></v-radio>
                      <v-radio label="Not sure" value="Not sure"></v-radio>
                    </v-radio-group>
                  </div>

                  <v-btn
                    color="primary"
                    x-large
                    @click="submitQuestionnaire"
                    :disabled="!isQuestionnaireComplete"
                    class="mt-2"
                  >
                    Submit Questionnaire
                  </v-btn>
                </div>

                <!-- Show this after questionnaire is completed -->
                <div v-if="questionnaireCompleted" class="mt-4">
                  <p v-if="sessionType === 'prolific'" class="text-subtitle-1 mb-4">
                    <span class="font-weight-bold">Please click <a :href="prolificRedirectUrl" target="_blank" class="primary--text">here</a> to complete your submission on Prolific.</span>
                  </p>
                  <p v-else class="text-subtitle-1 mb-4">
                    <span class="font-weight-bold">Thank you for your participation. You may now close this page.</span>
                  </p>
                  <v-btn
                    color="secondary"
                    x-large
                    @click="downloadMarketMetrics"
                    class="mt-2"
                  >
                    Download Metrics
                  </v-btn>
                </div>
              </div>
            </template>
            <template v-else>
              <v-btn
                color="primary"
                x-large
                @click="goToNextMarket"
                :loading="isNavigating"
                :disabled="!arePerMarketQuestionsComplete"
                class="mr-4"
              >
                Continue to Next Market
              </v-btn>
              <v-btn
                color="secondary"
                x-large
                @click="downloadMarketMetrics"
              >
                Download Metrics
              </v-btn>
            </template>
          </v-card-actions>
        </v-card>
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

// Get trader ID from session store
const traderId = computed(() => sessionStore.traderId || authStore.traderId)

const traderInfo = ref(null)
const orderBookMetrics = ref(null)
const traderSpecificMetrics = ref(null)
const httpUrl = import.meta.env.VITE_HTTP_URL
const prolificRedirectUrl = import.meta.env.VITE_PROLIFIC_REDIRECT_URL || 'https://app.prolific.com/submissions/complete?cc=C11I8OGE'
const showDialog = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const isNavigating = ref(false)

// Per-market questions state (shown after every market)
const perMarketQuestions = ref({
  marketDescription: null,
  imbalanceReason: null
})

// Check if inventory is imbalanced
const hasInventoryImbalance = computed(() => {
  const remaining = traderSpecificMetrics.value?.Remaining_Trades
  return remaining !== undefined && remaining !== null && remaining !== 0
})

// Check if per-market questions are complete
const arePerMarketQuestionsComplete = computed(() => {
  if (!perMarketQuestions.value.marketDescription) return false
  return true
})

// Questionnaire state (last market only)
const questionnaireCompleted = ref(false)
const questionnaire = ref({
  q1: null,
  q2: null,
  q3: null,
  q4: null
})

// Check if all questions are answered (per-market + final questionnaire)
const isQuestionnaireComplete = computed(() => {
  return arePerMarketQuestionsComplete.value &&
         questionnaire.value.q1 &&
         questionnaire.value.q2 &&
         questionnaire.value.q3 &&
         questionnaire.value.q4
})

// Submit questionnaire responses
async function submitQuestionnaire() {
  try {
    const responses = [
      questionnaire.value.q1,
      questionnaire.value.q2,
      questionnaire.value.q3,
      questionnaire.value.q4,
      perMarketQuestions.value.marketDescription,
      perMarketQuestions.value.imbalanceReason || 'N/A'
    ]
    
    let traderIdForSubmit = traderId.value
    
    // For prolific users, ensure correct format
    if (authStore.user?.isProlific) {
      const prolificPID = authStore.user.prolificData.PROLIFIC_PID
      traderIdForSubmit = `HUMAN_${prolificPID}`
    }
    
    const response = await axios.post(`${httpUrl}save_questionnaire_response`, {
      trader_id: traderIdForSubmit,
      responses: responses
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

// Download market metrics
const downloadMarketMetrics = async () => {
  try {
    const response = await axios.get(`${httpUrl}market_metrics`, {
      params: {
        trader_id: traderId.value,
        market_id: traderId.value
      },
      responseType: 'blob'
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
    //console.log('Trader Specific metrics:', traderSpecificMetrics.value) for printing the traderspecific metrics
    //console.log('Order Book metrics:', orderBookMetrics.value)

    // Retry for metrics if missing
    if (traderInfo.value && (!orderBookMetrics.value || !traderSpecificMetrics.value)) {
      let retryCount = 0
      const retryMetrics = async () => {
        if (retryCount >= maxRetries) return
        
        await new Promise(resolve => setTimeout(resolve, retryDelay))
        
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

// Save per-market question responses
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
      perMarketQuestions.value.imbalanceReason || 'N/A'
    ],
    market_number: currentMarket.value
  })
}

// Navigate to next market
const goToNextMarket = async () => {
  isNavigating.value = true

  try {
    // Save per-market responses before moving on
    await savePerMarketResponses().catch(e => console.warn('Failed to save responses:', e))

    // Check if user can start a new market
    if (!sessionStore.canStartNewMarket) {
      dialogTitle.value = 'Maximum Markets Reached'
      dialogMessage.value = 'You have completed the maximum number of markets allowed.'
      showDialog.value = true
      isNavigating.value = false
      return
    }

    // Try NavigationService first, fall back to page reload
    try {
      await NavigationService.startNextMarket()
    } catch (navError) {
      console.warn('NavigationService failed, falling back to reload:', navError)
      window.location.href = window.location.origin + '/onboarding/ready'
    }
  } catch (error) {
    console.error('Error navigating to next market:', error)
    // Fall back to reload instead of showing error dialog
    window.location.href = window.location.origin + '/onboarding/ready'
  }
}

const currentMarket = computed(() => {
  return traderInfo.value?.all_attributes?.historical_markets_count || 
         sessionStore.marketsCompleted || 
         1
})

const maxMarketsDisplay = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin || authStore.isAdmin) {
    return '∞'
  }
  return traderInfo.value?.all_attributes?.params?.max_markets_per_human || 
         sessionStore.maxMarkets || 
         'Loading...'
})

const sessionType = computed(() => {
  return traderInfo.value?.all_attributes?.params?.session_type || 'prolific'
})

const isLastMarket = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin || authStore.isAdmin) return false
  const currentCount = traderInfo.value?.all_attributes?.historical_markets_count || sessionStore.marketsCompleted || 1
  const maxMarkets = traderInfo.value?.all_attributes?.params?.max_markets_per_human || sessionStore.maxMarkets || 4
  return currentCount >= maxMarkets
})

async function checkQuestionnaireStatus() {
  try {
    let tid = traderId.value
    if (authStore.user?.isProlific) {
      tid = `HUMAN_${authStore.user.prolificData.PROLIFIC_PID}`
    }
    if (!tid) return
    const response = await axios.get(`${httpUrl}questionnaire/status`, { params: { trader_id: tid } })
    if (response.data?.data?.completed) {
      questionnaireCompleted.value = true
    }
  } catch (e) {
    // silently ignore - don't block the page
  }
}

onMounted(() => {
  fetchTraderInfo()
  checkQuestionnaireStatus()
})

</script>

<style scoped>
.market-summary-card {
  background: var(--color-bg-surface) !important;
  border: var(--border-width) solid var(--color-border) !important;
  border-radius: var(--radius-xl) !important;
  overflow: hidden;
  transition: border-color var(--transition-base);
  max-width: 800px;
  width: 100%;
}

.market-summary-card:hover {
  border-color: var(--color-border-strong);
}

.market-summary-card .v-card-title {
  background: var(--color-bg-elevated) !important;
  color: var(--color-text-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: var(--text-xl) !important;
  letter-spacing: var(--tracking-wide) !important;
  text-transform: uppercase !important;
  border-bottom: var(--border-width) solid var(--color-border) !important;
}

.metric-card {
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--transition-fast);
}

.metric-card:hover {
  border-color: var(--color-border-strong);
}

.metric-card h3 {
  color: var(--color-text-secondary) !important;
  font-size: var(--text-xs) !important;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
}

.metric-card .text-subtitle-1 {
  color: var(--color-text-secondary) !important;
}

.metric-card .text-h6 {
  color: var(--color-text-primary) !important;
  font-family: var(--font-mono) !important;
}

.questionnaire-section {
  text-align: left;
  color: var(--color-text-primary);
}

.questionnaire-section h3 {
  color: var(--color-text-primary) !important;
}

.questionnaire-section p {
  color: var(--color-text-secondary) !important;
}

.question-container {
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  padding: 1rem;
  border-radius: var(--radius-lg);
}

.market-summary-card .text-h5 {
  color: var(--color-primary) !important;
}

.market-summary-card .text-subtitle-1 {
  color: var(--color-text-secondary) !important;
}

.market-summary-card a {
  color: var(--color-primary) !important;
}
</style>
