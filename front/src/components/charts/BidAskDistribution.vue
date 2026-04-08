<template>
  <v-card class="bid-ask-chart-container" elevation="3">
    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watchEffect, onBeforeUnmount } from 'vue'
import { useMarketStore } from '@/store/market'
import { storeToRefs } from 'pinia'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const { chartData, midPoint } = storeToRefs(useMarketStore())
const chartCanvas = ref(null)
let chart = null

function buildChart() {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (chart) chart.destroy()

  // Extract bid and ask series from chartData
  const bidSeries = chartData.value.find(s => s.name === 'Bids') || { data: [] }
  const askSeries = chartData.value.find(s => s.name === 'Asks') || { data: [] }

  // Merge all price points
  const allPoints = new Map()
  for (const pt of bidSeries.data) allPoints.set(pt.x, { bid: pt.y, ask: 0 })
  for (const pt of askSeries.data) {
    const entry = allPoints.get(pt.x) || { bid: 0, ask: 0 }
    entry.ask = pt.y
    allPoints.set(pt.x, entry)
  }

  const sorted = [...allPoints.entries()].sort((a, b) => a[0] - b[0])
  const labels = sorted.map(([x]) => x)
  const bids = sorted.map(([, v]) => v.bid)
  const asks = sorted.map(([, v]) => v.ask)

  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Bids',
          data: bids,
          backgroundColor: 'rgba(34, 197, 94, 0.6)',
          borderColor: 'rgba(34, 197, 94, 0.9)',
          borderWidth: 1,
        },
        {
          label: 'Asks',
          data: asks,
          backgroundColor: 'rgba(239, 68, 68, 0.6)',
          borderColor: 'rgba(239, 68, 68, 0.9)',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#FFFFFF',
          titleColor: '#0F172A',
          bodyColor: '#0F172A',
          borderColor: '#E2E8F0',
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          ticks: { color: '#64748B', font: { size: 10, family: "'JetBrains Mono', monospace" } },
          grid: { display: false },
        },
        y: {
          ticks: { color: '#64748B', font: { size: 10, family: "'JetBrains Mono', monospace" }, precision: 0 },
          grid: { color: '#F1F5F9' },
        },
      },
    },
  })
}

onMounted(() => buildChart())

watchEffect(() => {
  // Trigger on chartData or midPoint changes
  if (chartData.value && chart) {
    const bidSeries = chartData.value.find(s => s.name === 'Bids') || { data: [] }
    const askSeries = chartData.value.find(s => s.name === 'Asks') || { data: [] }

    const allPoints = new Map()
    for (const pt of bidSeries.data) allPoints.set(pt.x, { bid: pt.y, ask: 0 })
    for (const pt of askSeries.data) {
      const entry = allPoints.get(pt.x) || { bid: 0, ask: 0 }
      entry.ask = pt.y
      allPoints.set(pt.x, entry)
    }

    const sorted = [...allPoints.entries()].sort((a, b) => a[0] - b[0])
    chart.data.labels = sorted.map(([x]) => x)
    chart.data.datasets[0].data = sorted.map(([, v]) => v.bid)
    chart.data.datasets[1].data = sorted.map(([, v]) => v.ask)
    chart.update('none')
  }
})

onBeforeUnmount(() => {
  if (chart) chart.destroy()
})
</script>

<style scoped>
.bid-ask-chart-container {
  width: 100%;
  background: var(--color-bg-surface);
  font-family: var(--font-mono);
}

.chart-wrapper {
  padding: 4px;
  height: 250px;
}
</style>
