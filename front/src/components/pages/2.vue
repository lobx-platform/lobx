<template>
  <div class="page-container">
    <div class="header-section">
      <h2 class="text-h4 page-heading">Trading Platform Guide</h2>
    </div>

    <v-container class="content-grid">
      <v-row>
        <!-- Introduction Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">What is the Trading Platform?</span>
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

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform</span>
              </div>
              <v-img
                :src="Intro"
                alt="Trading Platform Screenshot 1"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
              <p class="text-body-2 text-center mt-4 font-italic">
                This demonstration shows the trading platform in action.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 1</span>
              </div>
              <v-img
                :src="Timer"
                alt="Trading Platform Screenshot 2"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 2</span>
              </div>
              <v-img
                :src="Bars"
                alt="Trading Platform Screenshot 3"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 3</span>
              </div>
              <v-img
                :src="Plot"
                alt="Trading Platform Screenshot 4"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 4</span>
              </div>
              <v-img
                :src="Trades"
                alt="Trading Platform Screenshot 5"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 5</span>
              </div>
              <v-img
                :src="Messages"
                alt="Trading Platform Screenshot 6"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 6</span>
              </div>
              <v-img
                :src="Buttons"
                alt="Trading Platform Screenshot 7"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Trading Platform: Panel 7</span>
              </div>
              <v-img
                :src="Orders"
                alt="Trading Platform Screenshot 8"
                max-width="850"
                contain
                class="mx-auto rounded-lg"
              ></v-img>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import demoGif from '@/assets/demo.gif'
import Intro from '@/assets/Intro.jpg'
import Timer from '@/assets/Timer.jpg'
import Bars from '@/assets/Bars.jpg'
import Plot from '@/assets/Plot.jpg'
import Trades from '@/assets/Trades.jpg'
import Messages from '@/assets/Messages.jpg'
import Buttons from '@/assets/Buttons.jpg'
import Orders from '@/assets/Orders.jpg'
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
</style>
