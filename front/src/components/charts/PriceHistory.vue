<template>
  <div class="price-chart">
    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useTraderStore } from '@/store/app'
import { useMarketStore } from '@/store/market'
import { storeToRefs } from 'pinia'
import { Chart, registerables } from 'chart.js'
import 'chartjs-adapter-date-fns'

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
          borderColor: '#1a1a1a',
          borderWidth: 1.5,
          pointRadius: 2,
          pointBackgroundColor: '#1a1a1a',
          pointBorderColor: '#1a1a1a',
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
          backgroundColor: '#FFFFFF',
          titleColor: '#1a1a1a',
          bodyColor: '#1a1a1a',
          borderColor: '#E5E5E5',
          borderWidth: 1,
          padding: 6,
          displayColors: false,
          titleFont: {
            size: 10,
            family: "'IBM Plex Mono', monospace",
            weight: 'normal',
          },
          bodyFont: {
            size: 11,
            family: "'IBM Plex Mono', monospace",
            weight: 'bold',
          },
          callbacks: {
            title: () => '',
            label: (context) => `${Math.round(context.raw.y)}`,
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
              family: "'IBM Plex Mono', monospace",
            },
            color: '#999999',
          },
        },
        y: {
          position: 'left',
          grid: {
            color: '#F0F0F0',
            drawBorder: false,
          },
          ticks: {
            font: {
              size: 10,
              family: "'IBM Plex Mono', monospace",
            },
            color: '#999999',
            callback: (value) => `${Math.round(value)}`,
            maxTicksLimit: 8,
            precision: 0,
            stepSize: Math.ceil(
              (Math.max(...data.map((d) => d.y)) - Math.min(...data.map((d) => d.y))) / 8,
            ),
          },
          beginAtZero: false,
          grace: '5%',
        },
      },
      elements: {
        point: {
          hoverRadius: 4,
        },
      },
    },
  })
}

watch(
  history,
  (newHistory) => {
    if (newHistory && newHistory.length && chartCanvas.value) {
      const t0 = newHistory.length ? new Date(newHistory[0].timestamp).getTime() : 0
      const data = newHistory.map((item) => ({
        x: new Date(new Date(item.timestamp).getTime() - t0),
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
  { deep: true },
)

onMounted(() => {
  if (history.value && history.value.length) {
    const t0 = new Date(history.value[0].timestamp).getTime()
    const data = history.value.map((item) => ({
      x: new Date(new Date(item.timestamp).getTime() - t0),
      y: Math.round(item.price),
    }))
    createChart(data)
  }
})
</script>

<style scoped>
.price-chart {
  width: 100%;
  background: var(--color-bg-surface);
  font-family: var(--font-mono);
}

.chart-wrapper {
  padding: 4px;
  height: 250px;
}
</style>
