<template>
  <v-card class="bid-ask-chart-container" elevation="3">
    <div class="chart-wrapper">
      <highcharts-chart
        :constructor-type="'chart'"
        :options="chartOptions"
        :deepCopyOnUpdate="true"
      ></highcharts-chart>
    </div>
  </v-card>
</template>

<script setup>
import { reactive, watchEffect } from 'vue'
import { useMarketStore } from '@/store/market'
import { storeToRefs } from 'pinia'
import { Chart as HighchartsChart } from 'highcharts-vue'
import Highcharts from 'highcharts'

const { chartData, midPoint } = storeToRefs(useMarketStore())

const chartOptions = reactive({
  chart: {
    type: 'column',
    animation: false,
    backgroundColor: 'transparent',
    style: {
      fontFamily: "'JetBrains Mono', monospace",
    },
    height: 250,
    marginTop: 10,
    marginBottom: 30,
  },
  accessibility: {
    enabled: false,
  },
  title: {
    text: null,
  },
  xAxis: {
    allowDecimals: false,
    tickInterval: 1,
    minPadding: 0.1,
    maxPadding: 0.1,
    labels: {
      formatter: function () {
        return this.value.toString()
      },
      style: {
        color: '#64748B',
        fontSize: '10px',
      },
    },
    lineColor: 'rgba(255,255,255,0.08)',
    tickColor: 'rgba(255,255,255,0.08)',
  },
  yAxis: {
    title: null,
    labels: {
      format: '{value:.0f}',
      style: {
        color: '#64748B',
        fontSize: '10px',
      },
    },
    gridLineColor: 'rgba(255,255,255,0.04)',
  },
  credits: {
    enabled: false,
  },
  legend: {
    enabled: false,
  },
  tooltip: {
    shared: true,
    backgroundColor: '#1E293B',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    shadow: false,
    useHTML: true,
    headerFormat: '<table><tr><th colspan="2" style="color:#E2E8F0">{point.key:.2f}</th></tr>',
    pointFormat:
      '<tr><td style="color: {series.color}">{series.name}: </td>' +
      '<td style="text-align: right; color:#F8FAFC"><b>{point.y:.0f}</b></td></tr>',
    footerFormat: '</table>',
    style: {
      fontSize: '11px',
      color: '#E2E8F0',
    },
  },
  plotOptions: {
    column: {
      animation: false,
      pointPadding: 0.01,
      groupPadding: 0,
      borderWidth: 1,
      grouping: false,
    },
  },
  series: chartData.value,
})

watchEffect(() => {
  chartOptions.series = chartData.value.map((series) => ({
    ...series,
    pointPlacement: 0,
    color: series.name === 'Bids' ? 'rgba(34, 197, 94, 0.7)' : 'rgba(239, 68, 68, 0.7)',
    borderColor: series.name === 'Bids' ? 'rgba(34, 197, 94, 0.9)' : 'rgba(239, 68, 68, 0.9)',
  }))

  chartOptions.xAxis.plotBands = [
    {
      from: -Infinity,
      to: midPoint.value,
      color: 'rgba(34, 197, 94, 0.05)',
    },
    {
      from: midPoint.value,
      to: Infinity,
      color: 'rgba(239, 68, 68, 0.05)',
    },
  ]
})
</script>

<style scoped>
.bid-ask-chart-container {
  width: 100%;
  background: var(--color-bg-surface);
  font-family: var(--font-mono);
}

.chart-wrapper {
  padding: 0;
}

:deep(.highcharts-container) {
  font-family: 'JetBrains Mono', monospace !important;
}

:deep(.highcharts-axis-labels),
:deep(.highcharts-axis-title) {
  font-size: 10px !important;
  font-weight: 400 !important;
}

:deep(.highcharts-tooltip) {
  font-size: 11px !important;
}

:deep(.highcharts-background) {
  fill: transparent;
}
</style>
