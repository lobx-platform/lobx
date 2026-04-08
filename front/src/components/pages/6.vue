<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor">mdi-robot-industrial</v-icon>
        <h2 class="text-h4 page-heading">Market Participants</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Main Info Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-robot</v-icon>
                  <span class="text-h6">Artificial Traders</span>
                </div>
                <p class="text-body-1">
                  The other participants in the market are all artificial (algorithmic) traders,
                  i.e., non-human.
                </p>
                <v-alert color="info" variant="tonal" border="start" class="mt-4">
                  All artificial traders have no objective in terms of earnings.
                  <br /><br />
                  However, they may have tasks such as buying or selling a specific number of
                  shares, or both.
                  <br /><br />
                  For example, their trading activity can significantly shift the price either
                  upward or downward.
                </v-alert>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Behavior Cards
        <v-col cols="12" md="4">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card success-tint"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="success" class="mr-2">mdi-login</v-icon>
                  <span class="text-h6">Market Entry</span>
                </div>
                <p class="text-body-1">
                  Artificial traders join the market for the entire trading period.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <v-col cols="12" md="4">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card info-tint"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="info" class="mr-2">mdi-swap-horizontal</v-icon>
                  <span class="text-h6">Trading Activity</span>
                </div>
                <p class="text-body-1">
                  They buy and sell during their time in the market, 
                  which can significantly shift the price either upward or downward.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <v-col cols="12" md="4">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card warning-tint"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="warning" class="mr-2">mdi-logout</v-icon>
                  <span class="text-h6">Market Exit</span>
                </div>
                <p class="text-body-1">
                  They exit the market once they completed their task.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col> -->

        <!-- Next Steps Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-school</v-icon>
                  <span class="text-h6">Next Steps</span>
                </div>
                <v-timeline density="compact" align="start">
                  <v-timeline-item dot-color="success" icon="mdi-checkbox-marked-circle">
                    <div class="text-subtitle-1 font-weight-bold">Control Questions</div>
                    <div class="text-body-2">You will answer some control questions</div>
                  </v-timeline-item>

                  <v-timeline-item dot-color="info" icon="mdi-play-circle">
                    <div class="text-subtitle-1 font-weight-bold">Market</div>
                    <div class="text-body-2">
                      You will start trading to familiarize yourself with the trading platform
                    </div>
                  </v-timeline-item>
                </v-timeline>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
const props = defineProps({
  iconColor: String,
})
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
</style>
