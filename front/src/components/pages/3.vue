<template>
  <div class="page-container">
    <div class="header-section">
      <h2 class="section-title">General Trading Objectives</h2>
    </div>

    <v-container class="content-grid">
      <v-row>
        <!-- Overview Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Overview</span>
              </div>
              <p class="text-body-1">
                We are going to conduct <span class="highlight-text">{{ numMarkets }} markets</span>
                in which you will have a straightforward task.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Task Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Your Task</span>
              </div>
              <p class="text-body-1 font-weight-medium">
                At the beginning of each market you will be given a specific role.
                <br><br>
                Potential tasks for your role could include:
                <ul style="margin-left: 20px;">
                  <li style="margin-bottom: 10px; margin-top: 10px;">Buy a certain number of shares at the lowest price. (Informed Trader)</li>
                  <li style="margin-bottom: 10px;">Sell a certain number of shares at the highest price. (Informed Trader)</li>
                  <li>Buy and Sell shares to generate profit. (Speculator)</li>
                </ul>
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Informed Trader Task Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Task as a Informed Trader</span>
              </div>
              <div class="text-body-1 font-weight-medium">
                In this role, your task is to buy or sell a specific number of shares.
                <br><br>
                At the beginning of each market, you will be given a specific number of shares.
                <br><br>
                By the end of the market, you must ensure that you have achieved your goal.
                <br><br>
                <div style="border: 1px solid #f44336; background-color: #fdecea; color: #b71c1c; padding: 16px; border-radius: 4px; font-family: sans-serif;">
                <strong>Important Notice:</strong>
                <br><br>
                If, at the end of each market, you haven't completed your task, the platform will automatically buy or sell the remaining shares at a penalized price.
                This will affect your profits.
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Speculator Task Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Task as a Speculator</span>
              </div>
              <div class="text-body-1 font-weight-medium">
                In this role, your task is to buy and sell shares in order to make profits.
                <br><br>
                At the beginning of each market, you will be given a specific number of shares.
                <br><br>

                <div style="border: 1px solid #f44336; background-color: #fdecea; color: #b71c1c; padding: 16px; border-radius: 4px; font-family: sans-serif;">
                <strong>Important Notice:</strong>
                <br><br>
                At the end of each market, if the number of shares you hold is different from your initial amount, the platform will automatically adjust your balance at the prevailing bid or ask price.
                <br><br>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Objective Card -->
        <v-col cols="12" md="6">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Your Objective</span>
              </div>
              <p class="text-body-1 font-weight-medium">
                Sell at the highest price or buy at the lowest price.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Market Details Card -->
        <v-col cols="12" md="6">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Market Details</span>
              </div>
              <p class="text-body-1">
                All trading will be in terms of Liras and the length of each market will be
                <span class="highlight-text">{{ marketDuration }} minutes</span>.
              </p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";

const traderStore = useTraderStore();

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 0;
});

const numMarkets = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.max_markets_per_human || 0;
});

</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
</style>
