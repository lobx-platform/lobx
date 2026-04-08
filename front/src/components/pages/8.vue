<template>
  <div class="page-container">
    <div class="header-section">
      <h2 class="text-h4">Ready to Trade</h2>
    </div>

    <v-container class="content-grid">
      <v-row>
        <!-- Duration Card -->
        <v-col cols="12" md="6">
          <v-card elevation="2" class="info-card">
            <v-card-text>
              <span class="text-h6">Duration</span>
              <p class="text-body-1 mt-2">
                Trade for <strong>{{ marketDuration }} minutes</strong>
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Progress Card -->
        <v-col cols="12" md="6">
          <v-card elevation="2" class="info-card">
            <v-card-text>
              <span class="text-h6">Market Progress</span>
              <div class="d-flex justify-space-between align-center mt-2 mb-1">
                <span>Markets Played:</span>
                <strong>{{ currentMarket }}</strong>
              </div>
              <div class="d-flex justify-space-between align-center mb-3">
                <span>Markets Remaining:</span>
                <strong>{{ remainingMarkets }}</strong>
              </div>
              <v-progress-linear
                v-if="!isAdmin"
                :model-value="marketProgress"
                height="8"
                rounded
                color="primary"
              ></v-progress-linear>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Trading Parameters -->
        <v-col cols="12">
          <v-card elevation="2" class="info-card">
            <v-card-text>
              <span class="text-h6">Trading Parameters</span>
              <v-table density="compact" class="mt-2">
                <tbody>
                  <tr v-for="item in items" :key="item.parameter">
                    <td>{{ item.parameter }}</td>
                    <td><strong>{{ item.value }}</strong></td>
                  </tr>
                </tbody>
              </v-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Waiting Room Status (multi-participant) -->
      <div v-if="waitingRoom.needed > 1" class="waiting-status mt-4">
        <v-card elevation="2" class="info-card">
          <v-card-text class="text-center">
            <span class="text-h6">Participants</span>
            <p class="text-h4 mt-2 mb-1">{{ waitingRoom.joined }} / {{ waitingRoom.needed }}</p>
            <p v-if="waitingRoom.joined < waitingRoom.needed" class="text-body-2 text--secondary">
              Waiting for {{ waitingRoom.needed - waitingRoom.joined }} more...
            </p>
            <p v-else class="text-body-2" style="color: var(--color-success)">
              All participants joined. Click Start Trading when ready.
            </p>
          </v-card-text>
        </v-card>
      </div>

      <!-- Start Trading Button -->
      <div class="action-section mt-6 text-center">
        <v-btn
          @click="startTrading"
          :loading="isLoading"
          :disabled="!canStartTrading"
          color="primary"
          size="x-large"
          elevation="2"
          class="start-button"
        >
          {{ startButtonText }}
        </v-btn>

        <v-btn
          @click="handleLogout"
          color="error"
          variant="text"
          class="mt-2"
          :disabled="isLoading"
        >
          Logout
        </v-btn>
      </div>
    </v-container>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, reactive } from 'vue'
import { useTraderStore } from '@/store/app'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { wsBus } from '@/socket'
import NavigationService from '@/services/navigation'

const traderStore = useTraderStore()
const sessionStore = useSessionStore()
const authStore = useAuthStore()

const props = defineProps({
  traderAttributes: Object,
  iconColor: String,
})

const isLoading = ref(false)

// Waiting room state (for multi-participant sessions)
const waitingRoom = reactive({
  joined: 1,
  needed: 1,
  readyCount: 0,
})

// Listen for waiting room updates from Socket.IO
const onWaitingRoomUpdate = (data) => {
  waitingRoom.joined = data.current_users || data.joined || 1
  waitingRoom.needed = data.total_needed || data.needed || 1
  waitingRoom.readyCount = data.ready_count || 0
}

onMounted(() => {
  wsBus.on('waiting_room_update', onWaitingRoomUpdate)

  // Set initial needed count from predefined_goals
  const goals = traderStore.gameParams?.predefined_goals ||
    props.traderAttributes?.all_attributes?.params?.predefined_goals || [0]
  waitingRoom.needed = goals.length
})

onUnmounted(() => {
  wsBus.off('waiting_room_update', onWaitingRoomUpdate)
})

// Watch for market started signal
watch(
  () => traderStore.shouldRedirectToTrading,
  (shouldRedirect) => {
    if (shouldRedirect) {
      traderStore.setShouldRedirectToTrading(false)
      NavigationService.onMarketStarted()
    }
  }
)

watch(
  () => traderStore.isTradingStarted,
  (started) => {
    if (started && !traderStore.isWaitingForOthers) {
      NavigationService.onMarketStarted()
    }
  }
)

const marketDuration = computed(() => {
  return (
    traderStore.gameParams?.trading_day_duration ||
    props.traderAttributes?.all_attributes?.params?.trading_day_duration ||
    '...'
  )
})

const initialShares = computed(() => props.traderAttributes?.shares ?? '...')
const initialCash = computed(() => props.traderAttributes?.cash ?? '...')

const canStartTrading = computed(() => {
  if (!props.traderAttributes) return false
  // Multi-participant: need all participants joined
  if (waitingRoom.needed > 1 && waitingRoom.joined < waitingRoom.needed) return false
  return true
})

const startButtonText = computed(() => {
  if (isLoading.value) return 'Starting...'
  if (traderStore.isWaitingForOthers) return 'Waiting for others...'
  if (waitingRoom.needed > 1 && waitingRoom.joined < waitingRoom.needed) {
    return `Waiting for ${waitingRoom.needed - waitingRoom.joined} more...`
  }
  return 'Start Trading'
})

const isAdmin = computed(() => authStore.isAdmin)
const maxMarkets = computed(() => props.traderAttributes?.all_attributes?.params?.max_markets_per_human || 6)
const currentMarket = computed(() => props.traderAttributes?.all_attributes?.historical_markets_count || 0)
const remainingMarkets = computed(() => Math.max(0, maxMarkets.value - currentMarket.value))
const marketProgress = computed(() => (currentMarket.value / maxMarkets.value) * 100)

const items = computed(() => {
  const baseItems = [
    { parameter: 'Initial Shares', value: initialShares.value },
    { parameter: 'Initial Cash', value: initialCash.value ? `${initialCash.value} Liras` : '...' },
  ]

  const goalValue = props.traderAttributes?.goal
  if (goalValue !== undefined && goalValue !== null) {
    if (goalValue > 0) {
      baseItems.push({ parameter: 'Shares to Buy', value: goalValue })
    } else if (goalValue < 0) {
      baseItems.push({ parameter: 'Shares to Sell', value: Math.abs(goalValue) })
    }
  }

  return baseItems
})

const startTrading = async () => {
  if (!canStartTrading.value || isLoading.value) return

  isLoading.value = true

  try {
    await NavigationService.startTrading()

    // Fallback: check after a delay if we should navigate
    setTimeout(() => {
      if (traderStore.isTradingStarted && !traderStore.isWaitingForOthers) {
        NavigationService.onMarketStarted()
      }
    }, 5000)
  } catch (error) {
    console.error('Failed to start trading:', error)
    isLoading.value = false
  }
}

const handleLogout = async () => {
  await NavigationService.logout()
}
</script>

<style scoped>
.page-container {
  max-width: 800px;
  margin: 0 auto;
}

.header-section {
  text-align: center;
  margin-bottom: var(--space-6);
}

.info-card {
  background: var(--color-bg-surface);
}

.start-button {
  min-width: 240px;
}

.waiting-status .text-h4 {
  font-family: var(--font-mono);
  color: var(--color-primary);
}
</style>
