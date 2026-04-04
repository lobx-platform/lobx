<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor" class="pulse-icon">mdi-chart-box</v-icon>
        <h2 class="text-h4 gradient-text">Market Mechanics</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Time Limit Card -->
        <v-col cols="12" v-if="goalStatus !== 'noGoal'">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card warning-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="warning" class="mr-2">mdi-clock-alert</v-icon>
                  <span class="text-h6">Time Limit Not Met</span>
                </div>
                <p class="text-body-1">
                  If you do not achieve the objective within the time limit of the market, the
                  trading platform will automatically execute additional trades.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Market Earnings Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card success-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="success" class="mr-2">mdi-calculator</v-icon>
                  <span class="text-h6">Market Earnings Calculation</span>
                </div>
                <div class="earnings-formula pa-4 rounded-lg">
                  <div class="formula-title text-h6 mb-2">Market earnings =</div>
                  <div
                    v-if="goalStatus === 'noGoal' || goalStatus === 'unknown'"
                    class="formula-content"
                  >
                    Net profit or loss from all trades
                  </div>
                  <div v-else-if="goalStatus === 'selling'" class="formula-content">
                    Revenue from sales
                    <span class="formula-note">(incl. automatically sold shares)</span> <br />−
                    <span class="formula-highlight">(Number of shares)</span> ×
                    <span class="formula-highlight">(Mid-price at the beginning)</span>
                  </div>
                  <div v-else class="formula-content">
                    <span class="formula-highlight">(Number of shares)</span> ×
                    <span class="formula-highlight">(Mid-price at the beginning)</span>
                    <br />− Cost of purchases
                    <span class="formula-note">(incl. automatically bought shares)</span>
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Trading Dynamics Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card info-gradient">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="info" class="mr-2">
                    {{
                      goalStatus === 'noGoal'
                        ? 'mdi-chart-line'
                        : tradeAction === 'Selling'
                          ? 'mdi-arrow-down-bold'
                          : 'mdi-arrow-up-bold'
                    }}
                  </v-icon>
                  <span class="text-h6">
                    {{ goalStatus === 'noGoal' ? 'Market Dynamics' : 'Trading Objective' }}
                  </span>
                </div>
                <p class="text-body-1" v-if="goalStatus === 'noGoal' || goalStatus === 'unknown'">
                  The market price may fluctuate above or below the initial mid-price. 
                  These fluctuations can lead to potential gains or losses on your trades.
                </p>
                <template v-else-if="hasGoal">
                  <p class="text-body-1">
                    <span v-if="remainingShares !== '' && remainingShares > 0">
                      You need to {{ tradeVerb }}
                      <span class="highlight-text">{{ remainingShares }} shares</span> to reach your
                      goal.
                    </span>
                    <span v-else>
                      Your task is to {{ tradeVerb }}
                      <span class="highlight-text">{{ targetShares }} shares</span>.
                    </span>
                  </p>
                </template>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Initial Resources Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-wallet</v-icon>
                  <span class="text-h6">Initial Resources</span>
                </div>
                <p class="text-body-1">
                  <span v-if="goalStatus === 'noGoal'">
                    You will be given
                    <span class="highlight-text">{{ initialLiras }} Liras</span> and
                    <span class="highlight-text">{{ numShares }} shares</span>.
                  </span>
                  <span v-else-if="tradeAction === 'Selling'">
                    You will be given
                    <span class="highlight-text">{{ Math.abs(numShares) }} shares</span>.
                  </span>
                  <span v-else>
                    You will be given <span class="highlight-text">{{ initialLiras }} Liras</span>.
                  </span>
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Image Card 1 -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="text-h6 mb-4">Market Dynamics 1 (Clear Upward Trending)</div>

                <v-row>
                  <v-col cols="12" md="6">
                    <img src="@/assets/buy_1min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 1 minute </div>
                  </v-col>
                  <v-col cols="12" md="6">
                    <img src="@/assets/buy_2_5min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 2.5 minutes </div>
                  </v-col>
                </v-row>

                <!-- Strategy Hint -->
                <div class="strategy-hint-box mt-5">
                  <div class="strategy-hint-header">
                    <v-icon color="amber-darken-2" size="20" class="mr-2">mdi-lightbulb-on</v-icon>
                    <span class="strategy-hint-title">Strategy Insight</span>
                  </div>
                  <div class="strategy-hint-body">
                    Both charts show a clear <strong>upward trend</strong> in price. The best strategy here
                    is to <strong>buy shares early</strong> and hold them as the price rises, allowing you
                    to sell at a higher value and maximise your profit.
                  </div>
                </div>

              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Image Card 2 -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="text-h6 mb-4">Market Dynamics 2 (Unclear Upward Trending)</div>

                <v-row>
                  <v-col cols="12" md="6">
                    <img src="@/assets/unclear_buy_1min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 1 minute </div>
                  </v-col>
                  <v-col cols="12" md="6">
                    <img src="@/assets/unclear_buy_2_5min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 2.5 minutes </div>
                  </v-col>
                </v-row>

                <!-- Strategy Hint -->
                <div class="strategy-hint-box mt-5">
                  <div class="strategy-hint-header">
                    <v-icon color="amber-darken-2" size="20" class="mr-2">mdi-lightbulb-on</v-icon>
                    <span class="strategy-hint-title">Strategy Insight</span>
                  </div>
                  <div class="strategy-hint-body">
                    Although there is buying pressure, the price direction is not clear. The best strategy here
                    is to <strong>wait</strong> or <strong>send limit orders</strong>.
                  </div>
                </div>

              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Image Card 3 -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="text-h6 mb-4">Market Dynamics 3 (Clear Downward Trending)</div>

                <v-row>
                  <v-col cols="12" md="6">
                    <img src="@/assets/sell_1min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 1 minute </div>
                  </v-col>
                  <v-col cols="12" md="6">
                    <img src="@/assets/sell_2_5min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 2.5 minutes </div>
                  </v-col>
                </v-row>

                <!-- Strategy Hint -->
                <div class="strategy-hint-box mt-5">
                  <div class="strategy-hint-header">
                    <v-icon color="amber-darken-2" size="20" class="mr-2">mdi-lightbulb-on</v-icon>
                    <span class="strategy-hint-title">Strategy Insight</span>
                  </div>
                  <div class="strategy-hint-body">
                    Both charts show a clear <strong>downward trend</strong> in price. The best strategy here
                    is to <strong>sell shares early</strong> and hold them as the price drops, allowing you
                    to buy at a lower value and maximise your profit.
                  </div>
                </div>

              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Image Card 4 -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="text-h6 mb-4">Market Dynamics 4 (Unclear Downward Trending)</div>

                <v-row>
                  <v-col cols="12" md="6">
                    <img src="@/assets/unclear_sell_1min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 1 minute </div>
                  </v-col>
                  <v-col cols="12" md="6">
                    <img src="@/assets/unclear_sell_2_5min.png" style="width: 100%;" />
                    <div class="text-caption text-center mt-2"> Price movement after 2.5 minutes </div>
                  </v-col>
                </v-row>

                <!-- Strategy Hint -->
                <div class="strategy-hint-box mt-5">
                  <div class="strategy-hint-header">
                    <v-icon color="amber-darken-2" size="20" class="mr-2">mdi-lightbulb-on</v-icon>
                    <span class="strategy-hint-title">Strategy Insight</span>
                  </div>
                  <div class="strategy-hint-body">
                    Although there is selling pressure, the price initially <strong>dropped</strong>, then <strong>recovered upward</strong>, before
                    <strong>dropping again</strong>. This volatility makes timing critical. The best strategy is to
                    <strong>sell shares</strong> when the price is high.
                  </div>
                </div>

              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
        
        <!-- Final Earnings Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-cash-multiple</v-icon>
                  <span class="text-h6">Final Earnings</span>
                </div>
                <p class="text-body-1">
                  At the end of the study, you will be awarded earnings from one randomly selected
                  market. 
                  <br /><br />
                  Your earnings will be converted at a rate of
                  <span class="highlight-text">{{ conversionRate }} Liras = 1 GBP</span>.
                  <br /><br />
                  The minimum earning is your participation fee, which is
                  <span style="color: #1976d2; font-weight: 600; font-size: 1.1rem">5 GBP</span>.
                  <br /><br />
                  For each market, your earnings will be capped at
                  <span style="color: #1976d2; font-weight: 600; font-size: 1.1rem">10 GBP</span>.
                  <br /><br />
                  Thus, from each market you can earn up to
                  <span style="color: #1976d2; font-weight: 600; font-size: 1.1rem">15 GBP</span>.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTraderStore } from '@/store/app'
import { storeToRefs } from 'pinia'

const props = defineProps({
  traderAttributes: Object,
  iconColor: String,
})

const traderStore = useTraderStore()
const { goalMessage } = storeToRefs(traderStore)

const numShares = computed(() => props.traderAttributes?.shares ?? '#')
const initialShares = computed(() => props.traderAttributes?.initial_shares ?? '#')
const initialLiras = computed(() => props.traderAttributes?.cash ?? '#')
const conversionRate = computed(
  () => props.traderAttributes?.all_attributes?.params?.conversion_rate || 'X'
)

const normalizeNumeric = (value) => {
  if (value === null || value === undefined) return 0
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isNaN(parsed) ? 0 : parsed
  }
  return 0
}

const goalAmount = computed(() => {
  const paramsGoals = props.traderAttributes?.all_attributes?.params?.predefined_goals
  const traderId = props.traderAttributes?.id

  if (Array.isArray(paramsGoals) && paramsGoals.length && traderId) {
    const marketHumanTraders = traderStore.tradingMarketData?.human_traders
    if (Array.isArray(marketHumanTraders) && marketHumanTraders.length) {
      const index = marketHumanTraders.findIndex((trader) => trader.id === traderId)
      if (index !== -1) {
        return normalizeNumeric(paramsGoals[index])
      }
    }

    if (props.traderAttributes?.all_attributes?.params?.trader_index !== undefined) {
      const index = props.traderAttributes.all_attributes.params.trader_index
      if (index >= 0 && index < paramsGoals.length) {
        return normalizeNumeric(paramsGoals[index])
      }
    }
  }

  if (props.traderAttributes?.goal !== undefined) {
    return normalizeNumeric(props.traderAttributes.goal)
  }

  return 0
})

const goalProgress = computed(() => normalizeNumeric(props.traderAttributes?.goal_progress))

const hasGoal = computed(() => !Number.isNaN(goalAmount.value) && goalAmount.value !== 0)

const goalStatus = computed(() => {
  if (!hasGoal.value) return 'noGoal'
  return goalAmount.value < 0 ? 'selling' : 'buying'
})

const tradeAction = computed(() => {
  if (goalStatus.value === 'selling' && hasGoal.value) return 'Selling'
  if (goalStatus.value === 'buying' && hasGoal.value) return 'Buying'
  return 'Trading'
})

const tradeVerb = computed(() => {
  if (goalStatus.value === 'selling' && hasGoal.value) return 'sell'
  if (goalStatus.value === 'buying' && hasGoal.value) return 'buy'
  return 'trade'
})

const targetShares = computed(() => {
  if (!hasGoal.value) return ''
  return Math.abs(goalAmount.value)
})

const remainingShares = computed(() => {
  if (!hasGoal.value) return ''
  const remaining = goalAmount.value - goalProgress.value
  return Math.max(Math.abs(remaining), 0)
})

const autoTradeMultiplier = computed(() => {
  if (goalStatus.value === 'selling') return '½×'
  if (goalStatus.value === 'buying') return '1.5×'
  return ''
})

const goalDescription = computed(() => {
  if (goalMessage.value?.text) return goalMessage.value.text

  if (hasGoal.value && remainingShares.value !== '') {
    const sharesText = `${remainingShares.value} ${remainingShares.value === 1 ? 'share' : 'shares'}`
    return `You need to ${tradeVerb.value} ${sharesText} to reach your goal.`
  }

  if (hasGoal.value && targetShares.value) {
    const sharesText = `${targetShares.value} ${targetShares.value === 1 ? 'share' : 'shares'}`
    return `Your task is to ${tradeVerb.value} ${sharesText}.`
  }

  return 'You can freely trade in this market. Your goal is to make a profit.'
})
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
.earnings-formula {
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
}

.formula-title {
  color: var(--color-primary);
}

.formula-content {
  padding-left: 1.5rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.formula-highlight {
  color: var(--color-primary);
  font-weight: 500;
}

.formula-note {
  font-size: 0.9em;
  font-style: italic;
  color: var(--color-text-muted);
}

.strategy-hint-box {
  background: rgba(245, 158, 11, 0.06);
  border-left: 4px solid var(--color-warning);
  border-radius: 8px;
  padding: 14px 18px;
  color: var(--color-text-primary);
}

.strategy-hint-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.strategy-hint-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--color-warning);
}

.strategy-hint-body {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}
</style>
