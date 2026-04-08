<template>
  <div class="market-info">
    <div class="info-grid">
      <div
        v-for="item in filteredParams"
        :key="item.var_name"
        class="info-cell"
      >
        <div class="info-label">
          {{ item.display_name }}
          <v-tooltip location="bottom" :text="item.explanation" max-width="300">
            <template v-slot:activator="{ props }">
              <span v-bind="props" class="info-hint">?</span>
            </template>
          </v-tooltip>
        </div>
        <div class="info-value" :class="getValueColor(item.value)">
          {{ formatValue(item.value) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useMarketStore } from '@/store/market'

const { extraParams } = storeToRefs(useMarketStore())

const filteredParams = computed(() => {
  return extraParams.value.filter((p) => p.var_name !== 'imbalance')
})

const imbalanceValue = computed(() => {
  const item = extraParams.value.find((p) => p.var_name === 'imbalance')
  return item && item.value ? Number(item.value) : 0
})

const imbalanceMessage = computed(() => {
  const val = imbalanceValue.value || 0

  if (val > 0) {
    return `You have ${val} shares in excess. \n Sell ${val} shares before the market ends. \n Penalty if not corrected: ${val * -5}`
  } else if (val < 0) {
    return `You have ${Math.abs(val)} shares in deficit. \n Buy ${Math.abs(val)} shares before the market ends. \n Penalty if not corrected: ${Math.abs(val) * -5}`
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
    return value > 0 ? 'val-green' : value < 0 ? 'val-red' : ''
  }
  return ''
}

onMounted(() => {
  // setup
})
</script>

<style scoped>
.market-info {
  font-family: var(--font-family);
  background: var(--color-bg-surface);
  padding: 10px 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.info-cell {
  text-align: center;
  padding: 4px;
}

.info-label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.info-hint {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--color-text-muted);
  opacity: 0.5;
  cursor: help;
  margin-left: 2px;
}

.info-value {
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.val-green {
  color: var(--color-bid);
}

.val-red {
  color: var(--color-ask);
}
</style>
