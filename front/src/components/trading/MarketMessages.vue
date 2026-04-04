<template>
  <v-card height="100%" elevation="3" class="market-info-card">
    <v-card-text class="market-info-content" ref="messageContainer">
      <div class="info-grid">
        <div
          v-for="item in filteredParams"
          :key="item.var_name"
          class="info-cell"
        >
          <div class="info-title">
            {{ item.display_name }}
            <v-tooltip location="bottom" :text="item.explanation" max-width="300">
              <template v-slot:activator="{ props }">
                <v-icon x-small v-bind="props" color="grey lighten-1">mdi-information-outline</v-icon>
              </template>
            </v-tooltip>
          </div>
          <div class="info-value" :class="getValueColor(item.value)">
            {{ formatValue(item.value) }}
          </div>
        </div>
      </div>

      <div class="guidance-msg">
        <div class="tip-title">💡 Trading Tip</div>
        <ul class="tip-list">
        <li>
        If you believe the market will go up:
        <span class="buy-text">Buy now</span> and sell later.
        </li>
        <li>
        If you believe the market will go down:
        <span class="sell-text">Sell now</span> and buy later.
         </li>
        </ul>
      </div>

      <!-- IMBALANCE MESSAGE -->
      <!--<div v-if="imbalanceValue !== 0" class="imbalance-msg" :class="imbalanceColorClass">
        {{ imbalanceMessage }}
      </div> -->
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useMarketStore } from '@/store/market'

const { extraParams } = storeToRefs(useMarketStore())

//filter params are extraParams without imbalance
// remove them if imbalance is needed
const filteredParams = computed(() => {
  return extraParams.value.filter(p => p.var_name !== 'imbalance')
})

const imbalanceValue = computed(() => {
  const item = extraParams.value.find(p => p.var_name === 'imbalance')
  return item && item.value ? Number(item.value) : 0
})

const imbalanceMessage = computed(() => {
  const val = imbalanceValue.value || 0
  
  if (val > 0) {
    return `⚠️ You have ${val} shares in excess. \n Sell ${val} shares before the market ends. \n Penalty if not corrected: ${val*(-5)}`
  } else if (val < 0) {
    return `⚠️ You have ${Math.abs(val)} shares in deficit. \n Buy ${Math.abs(val)} shares before the market ends. \n Penalty if not corrected: ${Math.abs(val)* (-5)}`
  } else {
    return `Your inventory is balanced.`
  }
})

const imbalanceColorClass = computed(() => {
  return imbalanceValue.value !== 0 ? 'imbalance-red' : 'imbalance-green'
})

const formatValue = (value) => {
  if (typeof value === 'number') {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }
  return value
}

const getValueColor = (value) => {
  if (typeof value === 'number') {
    return value > 0 ? 'green--text' : value < 0 ? 'red--text' : ''
  }
  return ''
}

onMounted(() => {
  // Any necessary setup
})
</script>

<style scoped>
.market-info-card {
  background: var(--color-bg-surface);
  font-family: var(--font-family);
}

.market-info-content {
  padding: var(--space-3) var(--space-2);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}

.info-cell {
  text-align: center;
  padding: var(--space-1);
}

.info-title {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  margin-bottom: 3px;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.info-value {
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-bright);
}

.v-icon.v-icon--size-x-small {
  font-size: 11px;
  margin-left: 2px;
  opacity: 0.5;
}

.imbalance-msg {
  text-align: left;
  margin-top: var(--space-2);
  white-space: pre-line;
}

.imbalance-red {
  color: var(--color-ask) !important;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  animation: flicker 3s infinite;
}

@keyframes flicker {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.imbalance-green {
  color: var(--color-bid) !important;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
}

.guidance-msg {
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-top: var(--space-2);
}

.tip-title {
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-1);
  color: var(--color-text-primary);
}

.tip-list {
  padding-left: 16px;
  margin: 0;
}

.tip-list li {
  margin-bottom: var(--space-1);
  color: var(--color-text-secondary);
}

.buy-text {
  color: var(--color-bid);
  font-weight: var(--font-semibold);
}

.sell-text {
  color: var(--color-ask);
  font-weight: var(--font-semibold);
}
</style>
