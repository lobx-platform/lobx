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
          borderColor: '#2196F3',
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: '#2196F3',
          pointBorderColor: '#2196F3',
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
          backgroundColor: 'white',
          titleColor: 'black',
          bodyColor: 'black',
          borderColor: '#E0E0E0',
          borderWidth: 1,
          padding: 12,
          displayColors: false,
          titleFont: {
            size: 16,
            family: "'Inter', sans-serif",
            weight: 'normal',
          },
          bodyFont: {
            size: 16,
            family: "'Inter', sans-serif",
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
              size: 12,
              family: "'Inter', sans-serif",
            },
            color: '#666',
          },
        },
        y: {
          position: 'left',
          grid: {
            display: false,
          },
          ticks: {
            font: {
              size: 12,
              family: "'Inter', sans-serif",
            },
            color: '#666',
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
  background-color: #ffffff;
  overflow: hidden;
  font-family: 'Inter', sans-serif;
}

.chart-wrapper {
  padding: 0;
  height: 250px;
}
</style>
