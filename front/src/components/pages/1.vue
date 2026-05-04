<template>
  <div v-html="content"></div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { marked } from "marked";
import { useTraderStore } from "@/store/app";

const traderStore = useTraderStore();

const content = ref("");

// same pattern as 3.vue: dynamic variables used in admin dashboard
const numMarkets = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.max_markets_per_human || 0;
});

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 0;
});

const initialCash = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.initial_cash || 0;
});

const initialStocks = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.initial_stocks || 0;
});

onMounted(async () => {
  try {
    const res = await fetch("/instructions/instructions.md");
    let text = await res.text();

    text = text
      .replace(/{numMarkets}/g, numMarkets.value)
      .replace(/{marketDuration}/g, marketDuration.value)
      .replace(/{initialCash}/g, initialCash.value)
      .replace(/{initialStocks}/g, initialStocks.value);

    content.value = marked.parse(text);

  } catch (e) {
    console.error(e);
    content.value = "ERROR";
  }
});
</script>