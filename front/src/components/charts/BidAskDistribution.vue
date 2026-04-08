<template>
  <div class="bid-ask-chart">
    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
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

// Custom plugin to draw background bands (blue left of midpoint, red right)
const backgroundBandsPlugin = {
  id: 'backgroundBands',
  beforeDraw(chart) {
    const { ctx, chartArea, scales } = chart
    if (!chartArea || !scales.x) return

    const mid = midPoint.value
    if (mid == null) return

    const labels = chart.data.labels || []
    // Find pixel position of midpoint
    const midIndex = labels.findIndex(l => l >= mid)
    let midPixel
    if (midIndex >= 0) {
      midPixel = scales.x.getPixelForValue(midIndex)
    } else {
      midPixel = chartArea.right
    }

    // Blue band (left of midpoint)
    ctx.save()
    ctx.fillStyle = 'rgba(33, 150, 243, 0.06)'
    ctx.fillRect(chartArea.left, chartArea.top, midPixel - chartArea.left, chartArea.height)

    // Red band (right of midpoint)
    ctx.fillStyle = 'rgba(244, 67, 54, 0.06)'
    ctx.fillRect(midPixel, chartArea.top, chartArea.right - midPixel, chartArea.height)
    ctx.restore()
  }
}

function buildData() {
  const bidSeries = chartData.value.find(s => s.name === 'Bids') || { data: [] }
  const askSeries = chartData.value.find(s => s.name === 'Asks') || { data: [] }

  // Merge all price points so both datasets share the same x labels
  const allPoints = new Map()
  for (const pt of bidSeries.data) allPoints.set(pt.x, { bid: pt.y, ask: 0 })
  for (const pt of askSeries.data) {
    const entry = allPoints.get(pt.x) || { bid: 0, ask: 0 }
    entry.ask = pt.y
    allPoints.set(pt.x, entry)
  }

  const sorted = [...allPoints.entries()].sort((a, b) => a[0] - b[0])
  return {
    labels: sorted.map(([x]) => x),
    bids: sorted.map(([, v]) => v.bid || null),  // null hides the bar instead of showing 0
    asks: sorted.map(([, v]) => v.ask || null),
  }
}

function buildChart() {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (chart) chart.destroy()

  const { labels, bids, asks } = buildData()

  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Bids',
          data: bids,
          backgroundColor: 'rgba(33, 150, 243, 0.7)',
          borderColor: 'rgba(25, 118, 210, 1)',
          borderWidth: 1,
          barPercentage: 0.95,
          categoryPercentage: 1.0,
        },
        {
          label: 'Asks',
          data: asks,
          backgroundColor: 'rgba(244, 67, 54, 0.7)',
          borderColor: 'rgba(211, 47, 47, 1)',
          borderWidth: 1,
          barPercentage: 0.95,
          categoryPercentage: 1.0,
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
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          titleColor: '#1a1a1a',
          bodyColor: '#1a1a1a',
          borderColor: '#E5E5E5',
          borderWidth: 1,
          padding: 8,
          titleFont: { family: "'IBM Plex Mono', monospace", size: 11 },
          bodyFont: { family: "'IBM Plex Mono', monospace", size: 11 },
        },
      },
      scales: {
        x: {
          ticks: {
            color: '#666',
            font: { size: 10, family: "'IBM Plex Mono', monospace" },
          },
          grid: { display: false },
          border: { color: '#ccd6eb' },
        },
        y: {
          ticks: {
            color: '#666',
            font: { size: 10, family: "'IBM Plex Mono', monospace" },
            precision: 0,
          },
          grid: { color: '#e6e6e6' },
          border: { display: false },
        },
      },
    },
    plugins: [backgroundBandsPlugin],
  })
}

onMounted(() => buildChart())

watchEffect(() => {
  if (chartData.value && chart) {
    const { labels, bids, asks } = buildData()
    chart.data.labels = labels
    chart.data.datasets[0].data = bids
    chart.data.datasets[1].data = asks
    chart.update('none')
  }
})

onBeforeUnmount(() => {
  if (chart) chart.destroy()
})
</script>

<style scoped>
.bid-ask-chart {
  width: 100%;
  background: var(--color-bg-surface);
  font-family: var(--font-mono);
}

.chart-wrapper {
  padding: 4px;
  height: 250px;
}
</style>
