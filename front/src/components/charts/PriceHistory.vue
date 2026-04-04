<template>
  <v-card class="history-chart-container" elevation="3">
    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useTraderStore } from '@/store/app'
import { useMarketStore } from '@/store/market'
import { storeToRefs } from 'pinia'
import { Chart, registerables } from 'chart.js'
import 'chartjs-adapter-date-fns'

// Register Chart.js components
Chart.register(...registerables)

const traderStore = useTraderStore()
const marketStore = useMarketStore()
const { history } = storeToRefs(marketStore)
const chartCanvas = ref(null)
let priceChart = null

const createChart = (data) => {
  if (priceChart) {
    priceChart.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')

  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Price',
          data: data,
          borderColor: '#22D3EE',
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#22D3EE',
          pointBorderColor: '#22D3EE',
          tension: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: {
        intersect: false,
        mode: 'index',
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          enabled: true,
          backgroundColor: '#1E293B',
          titleColor: '#E2E8F0',
          bodyColor: '#F8FAFC',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 10,
          displayColors: false,
          titleFont: {
            size: 12,
            family: "'JetBrains Mono', monospace",
            weight: 'normal',
          },
          bodyFont: {
            size: 13,
            family: "'JetBrains Mono', monospace",
            weight: 'bold',
          },
          callbacks: {
            title: () => '',
            label: (context) => `Price: $${Math.round(context.raw.y)}`,
          },
        },
      },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'second',
            displayFormats: {
              second: 'mm:ss',
            },
          },
          grid: {
            display: false,
          },
          ticks: {
            font: {
              size: 10,
              family: "'JetBrains Mono', monospace",
            },
            color: '#64748B',
          },
        },
        y: {
          position: 'left',
          grid: {
            color: 'rgba(255,255,255,0.04)',
            drawBorder: false,
          },
          ticks: {
            font: {
              size: 10,
              family: "'JetBrains Mono', monospace",
            },
            color: '#64748B',
            callback: (value) => `${Math.round(value)}`,
            maxTicksLimit: 8,
            precision: 0,
            stepSize: Math.ceil(
              (Math.max(...data.map((d) => d.y)) - Math.min(...data.map((d) => d.y))) / 8
            ),
          },
          beginAtZero: false,
          grace: '5%',
        },
      },
      elements: {
        point: {
          hoverRadius: 6,
        },
      },
    },
  })
}

watch(
  history,
  (newHistory) => {
    if (newHistory && newHistory.length && chartCanvas.value) {
      const data = newHistory.map((item) => ({
        x: new Date(item.timestamp),
        y: Math.round(item.price),
      }))

      if (priceChart) {
        priceChart.data.datasets[0].data = data
        priceChart.update('none')
      } else {
        createChart(data)
      }
    }
  },
  { deep: true }
)

onMounted(() => {
  if (history.value && history.value.length) {
    const data = history.value.map((item) => ({
      x: new Date(item.timestamp),
      y: Math.round(item.price),
    }))
    createChart(data)
  }
})
</script>

<style scoped>
.history-chart-container {
  width: 100%;
  background: var(--color-bg-surface);
  overflow: hidden;
  font-family: var(--font-mono);
}

.chart-wrapper {
  padding: var(--space-1);
  height: 250px;
}
</style>
