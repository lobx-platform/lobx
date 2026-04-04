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
    backgroundColor: '#FFFFFF',
    style: {
      fontFamily: 'Inter, sans-serif',
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
        color: '#666',
        fontSize: '10px',
      },
    },
    lineColor: '#ccd6eb',
    tickColor: '#ccd6eb',
  },
  yAxis: {
    title: null,
    labels: {
      format: '{value:.0f}',
      style: {
        color: '#666',
        fontSize: '10px',
      },
    },
    gridLineColor: '#e6e6e6',
  },
  credits: {
    enabled: false,
  },
  legend: {
    enabled: false,
  },
  tooltip: {
    shared: true,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderWidth: 0,
    shadow: true,
    useHTML: true,
    headerFormat: '<table><tr><th colspan="2">{point.key:.2f}</th></tr>',
    pointFormat:
      '<tr><td style="color: {series.color}">{series.name}: </td>' +
      '<td style="text-align: right"><b>{point.y:.0f}</b></td></tr>',
    footerFormat: '</table>',
    style: {
      fontSize: '12px',
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
    color: series.name === 'Bids' ? 'rgba(33, 150, 243, 0.8)' : 'rgba(244, 67, 54, 0.8)',
    borderColor: series.name === 'Bids' ? 'rgba(25, 118, 210, 1)' : 'rgba(211, 47, 47, 1)',
  }))

  chartOptions.xAxis.plotBands = [
    {
      from: -Infinity,
      to: midPoint.value,
      color: 'rgba(33, 150, 243, 0.1)',
    },
    {
      from: midPoint.value,
      to: Infinity,
      color: 'rgba(244, 67, 54, 0.1)',
    },
  ]
})
</script>

<style scoped>
.bid-ask-chart-container {
  width: 100%;
  background-color: #ffffff;
  font-family: 'Inter', sans-serif;
}

.chart-wrapper {
  padding: 0;
}

:deep(.highcharts-container) {
  font-family: 'Inter', sans-serif !important;
}

:deep(.highcharts-axis-labels),
:deep(.highcharts-axis-title) {
  font-size: 10px !important;
  font-weight: 400 !important;
}

:deep(.highcharts-tooltip) {
  font-size: 12px !important;
}
</style>
