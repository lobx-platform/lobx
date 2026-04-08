<template>
  <div class="page-container">
    <div class="header-section">
      <h2 class="text-h4 page-heading">LOBX Platform Guide</h2>
    </div>

    <v-container class="content-grid">
      <v-row>
        <!-- Introduction Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">What is LOBX?</span>
              </div>
              <p class="text-body-1">
                The trading platform is software that allows participants to trade with one
                another. It displays relevant information about the demand and supply of an asset
                (e.g. a share). What you see on the trading platform is common knowledge, meaning
                all other participants can see it.
                <br /><br />
                This trading platform closely replicates real financial exchange platforms, where
                participants trade under a double auction setting. In particular, a double auction
                trading mechanism allows buyers to submit bids (buy offers) and sellers to submit
                asks (sell offers) simultaneously. The platform matches buyers and sellers based
                on price and quantity.
                <br /><br />
                Please take some time to carefully read the next slides.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Orders Section -->
        <v-col cols="12" md="6">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Direct Orders</span>
              </div>
              <p class="text-body-1">
                You can directly accept an existing price to sell or buy, such as an order from
                another participant. In this case, the trade is immediately executed at the best
                bid or ask respectively.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Passive Orders</span>
              </div>
              <p class="text-body-1">
                You can place orders to sell or buy that are not immediately executed. This means
                you have to wait for someone to accept them.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Improving Orders -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Improving Orders</span>
              </div>
              <ul class="rules-list">
                <li>
                  Place an order to sell (ask) a share for a lower price than the current best ask
                </li>
                <li>
                  Place an order to buy (bid) a share for a higher price than the current best bid
                </li>
              </ul>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Interactive Trading Platform Preview -->
        <v-col cols="12">
          <span class="text-h6 font-weight-bold">LOBX Overview</span>
          <TradingPreview highlight="all" caption="This is the LOBX trading interface. Each panel shows different information about the market." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Status Bar</span>
          <TradingPreview highlight="header" caption="The top bar shows your role (Speculator), PnL (Profit and Loss), shares held, available cash, number of traders, and remaining time." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Buy-Sell Chart</span>
          <TradingPreview highlight="chart" caption="This panel shows all buy (bid) and sell (ask) orders in the market. The horizontal axis shows the price and vertical axis shows the number of shares." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Price History</span>
          <TradingPreview highlight="price-history" caption="This chart plots traded prices on the y-axis against time on the x-axis." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Your Trades</span>
          <TradingPreview highlight="trades" caption="This panel shows your trades along with the average prices sold and bought. For example, if you bought 4 shares at an average price of 101.25 and sold 4 shares at an average price of 100, you are making a loss." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Market Info</span>
          <TradingPreview highlight="market-info" caption="This panel shows the Last Traded Price, the Midprice (average between best buy and ask prices), and the Spread (difference between best sell and best buy price). It also provides trading tips." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Trading Panel</span>
          <TradingPreview highlight="trading-panel" caption="This panel contains buttons to buy or sell. For example, to buy a share immediately, press the first Buy button at the top price. Similarly, you can sell immediately at the top Sell price. You can also send passive orders at other price levels." />
        </v-col>

        <v-col cols="12">
          <span class="text-h6 font-weight-bold">Passive Orders</span>
          <TradingPreview highlight="orders" caption="This panel shows all passive orders you sent. These orders do not execute immediately — other traders must accept them. You can cancel them by clicking the minus button." />
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import TradingPreview from '@/components/TradingPreview.vue'
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
</style>
