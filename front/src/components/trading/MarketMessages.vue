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
  background-color: #ffffff;
  font-family: 'Inter', sans-serif;
}

.market-info-content {
  padding: 12px 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.info-cell {
  text-align: center;
}

.info-title {
  font-size: 11px;
  font-weight: 500;
  color: #666;
  margin-bottom: 4px;
}

.info-value {
  font-size: 16px;
  font-weight: 700;
}

.v-icon.v-icon--size-x-small {
  font-size: 12px;
  margin-left: 2px;
}

.imbalance-msg {
  text-align: left;
  margin-top: 8px;
  white-space: pre-line;
}

.imbalance-red {
  color: red !important;
  font-size: 13px;
  font-weight: 700;
  animation: flicker 3s infinite;
}

@keyframes flicker {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.imbalance-green {
  color: green !important;
  font-size: 14px;
  font-weight: 700;
}

.guidance-msg {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 14px 16px;
  border-radius: 12px;
  font-size: 0.9rem;
  color: #334155;
  margin-top: 10px;
}

.tip-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.tip-list {
  padding-left: 18px;
  margin: 0;
}

.tip-list li {
  margin-bottom: 6px;
}

.buy-text {
  color: blue;
  font-weight: 600;
}

.sell-text {
  color: #dc2626;
  font-weight: 600;
}

</style>
