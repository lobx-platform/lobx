<template>
  <div class="page-container">
    <div class="header-section">
      <h2 class="text-h4 page-heading">LOBX Platform Guide</h2>
    </div>

    <p class="text-body-1">
      The platform is divided into several components. Each one is explained below.
    </p>
    <br>


    <!-- Interactive Trading Platform Preview -->
    <div class="section">
      <span class="text-h6 font-weight-bold">LOBX Overview</span>
      <TradingPreview
        highlight="all"
        caption="This is the LOBX trading interface. Each panel shows different information about the market."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Status Bar</span>
      <TradingPreview
        highlight="header"
        caption="The top bar shows your role (Speculator), PnL (Profit and Loss), shares held, available cash, number of traders, and remaining time."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Buy-Sell Chart</span>
      <TradingPreview
        highlight="chart"
        caption="This panel shows all buy (bid) and sell (ask) orders in the market. The horizontal axis shows the price and vertical axis shows the number of shares."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Price History</span>
      <TradingPreview
        highlight="price-history"
        caption="This chart plots traded prices on the y-axis against time on the x-axis."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Your Trades</span>
      <TradingPreview
        highlight="trades"
        caption="This panel shows your trades along with the average prices sold and bought."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Market Info</span>
      <TradingPreview
        highlight="market-info"
        caption="This panel shows the Last Traded Price, Midprice, Spread, and trading tips."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Trading Panel</span>
      <TradingPreview
        highlight="trading-panel"
        caption="This panel contains buttons to buy or sell and allows sending passive orders."
      />
    </div>

    <div class="section">
      <span class="text-h6 font-weight-bold">Passive Orders</span>
      <TradingPreview
        highlight="orders"
        caption="This panel shows your passive orders. These do not execute immediately and can be canceled."
      />
    </div>
  </div>
</template>

<script setup>
import TradingPreview from '@/components/TradingPreview.vue'
</script>

<style scoped>
.section {
  margin-bottom: 2rem;
}
</style>