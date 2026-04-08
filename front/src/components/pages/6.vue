<template>
  <div class="page-container">
    <div class="header-section">
      <h2 class="text-h4 page-heading">Market Participants</h2>
    </div>

    <v-container class="content-grid">
      <v-row>
        <!-- Main Info Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Artificial Traders</span>
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
        </v-col>

        <!-- Next Steps Card -->
        <v-col cols="12">
          <v-card class="info-card" flat>
            <v-card-text>
              <div class="mb-4">
                <span class="text-h6 font-weight-bold">Next Steps</span>
              </div>
              <div class="next-steps-list">
                <div class="next-step-item">
                  <div class="text-subtitle-1 font-weight-bold">1. Control Questions</div>
                  <div class="text-body-2">You will answer some control questions</div>
                </div>
                <div class="next-step-item">
                  <div class="text-subtitle-1 font-weight-bold">2. Market</div>
                  <div class="text-body-2">
                    You will start trading to familiarize yourself with the trading platform
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
.next-steps-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.next-step-item {
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
}
</style>
