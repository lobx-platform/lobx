<!--
  TradingPreview — renders a mock trading dashboard with one panel highlighted.

  Usage:
    <TradingPreview highlight="trading-panel" caption="Click Buy/Sell to place orders." />

  Props:
    highlight: which panel to focus — 'all' | 'header' | 'trades' | 'market-info' | 'chart' | 'orders' | 'price-history' | 'trading-panel'
    caption: explanation text shown next to the highlighted panel
-->
<template>
  <div class="preview-wrapper">
    <div class="preview-frame" :class="{ 'no-highlight': highlight === 'all' }">
      <!-- Mock Header -->
      <div class="mock-header" :class="{ highlighted: highlight === 'header', dimmed: highlight !== 'header' && highlight !== 'all' }">
        <span class="mock-title">LOBX</span>
        <div class="mock-stats">
          <span>SPECULATOR</span>
          <span>PnL: -5</span>
          <span>Shares: 10 +0</span>
          <span>Cash: 1195</span>
          <span>Traders: 1/1</span>
          <span class="mock-timer">2:26</span>
        </div>
      </div>

      <!-- Mock Grid -->
      <div class="mock-grid">
        <!-- Row 1 -->
        <div class="mock-panel" :class="{ highlighted: highlight === 'trades', dimmed: highlight !== 'trades' && highlight !== 'all' }">
          <div class="mock-panel-title">Your Trades</div>
          <div class="mock-panel-body">
            <div class="mock-vwap">
              <span>Avg Price</span>
              <span class="bid-color">Buy: 101.25</span>
              <span>|</span>
              <span class="ask-color">Sell: 100.00</span>
            </div>
            <div class="mock-trades-columns">
              <div class="mock-trades-col">
                <div class="mock-trade-row bid-border">102 — 1sh</div>
                <div class="mock-trade-row bid-border">101 — 3sh</div>
              </div>
              <div class="mock-trades-col">
                <div class="mock-trade-row ask-border">100 — 2sh</div>
                <div class="mock-trade-row ask-border">99 — 1sh</div>
              </div>
            </div>
          </div>
        </div>

        <div class="mock-panel" :class="{ highlighted: highlight === 'chart', dimmed: highlight !== 'chart' && highlight !== 'all' }">
          <div class="mock-panel-title">Buy-Sell Chart</div>
          <div class="mock-panel-body mock-chart">
            <!-- Bids decrease left to right, Asks increase left to right -->
            <div class="mock-bar-group"><div class="mock-bar bid-bar" style="height: 80%"></div></div>
            <div class="mock-bar-group"><div class="mock-bar bid-bar" style="height: 60%"></div></div>
            <div class="mock-bar-group"><div class="mock-bar bid-bar" style="height: 30%"></div></div>
            <div class="mock-bar-group"><div class="mock-bar ask-bar" style="height: 25%"></div></div>
            <div class="mock-bar-group"><div class="mock-bar ask-bar" style="height: 55%"></div></div>
            <div class="mock-bar-group"><div class="mock-bar ask-bar" style="height: 75%"></div></div>
            <div class="mock-axis">97 &nbsp; 98 &nbsp; 99 &nbsp; 100 &nbsp; 101 &nbsp; 102</div>
          </div>
        </div>

        <div class="mock-panel" :class="{ highlighted: highlight === 'price-history', dimmed: highlight !== 'price-history' && highlight !== 'all' }">
          <div class="mock-panel-title">Market Trade Price History</div>
          <div class="mock-panel-body mock-line-chart">
            <svg viewBox="0 0 200 80" class="mock-svg">
              <polyline :points="pricePolyline" fill="none" stroke="#1a1a1a" stroke-width="1.5"/>
              <circle v-for="(p, i) in pricePoints" :key="i" :cx="p[0]" :cy="p[1]" r="2" fill="#1a1a1a"/>
            </svg>
          </div>
        </div>

        <!-- Row 2 -->
        <div class="mock-panel" :class="{ highlighted: highlight === 'market-info', dimmed: highlight !== 'market-info' && highlight !== 'all' }">
          <div class="mock-panel-title">Market Info</div>
          <div class="mock-panel-body">
            <div class="mock-info-grid">
              <div class="mock-info-cell">
                <div class="mock-info-label">Last Traded Price</div>
                <div class="mock-info-value">101</div>
              </div>
              <div class="mock-info-cell">
                <div class="mock-info-label">Midprice</div>
                <div class="mock-info-value">100.5</div>
              </div>
              <div class="mock-info-cell">
                <div class="mock-info-label">Spread</div>
                <div class="mock-info-value">1</div>
              </div>
            </div>
            <div class="mock-tip">
              <ul>
                <li>Market up → <strong class="bid-color">Buy now</strong>, sell later</li>
                <li>Market down → <strong class="ask-color">Sell now</strong>, buy later</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="mock-panel" :class="{ highlighted: highlight === 'orders', dimmed: highlight !== 'orders' && highlight !== 'all' }">
          <div class="mock-panel-title">Passive Orders</div>
          <div class="mock-panel-body">
            <div class="mock-orders-row">
              <span class="bid-color">BUY 97</span>
              <span class="mock-order-btns">+ −</span>
              <span class="ask-color">SELL 104</span>
              <span class="mock-order-btns">+ −</span>
            </div>
          </div>
        </div>

        <div class="mock-panel" :class="{ highlighted: highlight === 'trading-panel', dimmed: highlight !== 'trading-panel' && highlight !== 'all' }">
          <div class="mock-panel-title">Trading Panel</div>
          <div class="mock-panel-body">
            <div class="mock-button-grid">
              <div class="mock-buy-col">
                <div class="mock-price-btn"><span>101</span><span class="mock-btn-buy">Buy</span></div>
                <div class="mock-price-btn"><span>100</span><span class="mock-btn-buy">Buy</span></div>
                <div class="mock-price-btn"><span>99</span><span class="mock-btn-buy">Buy</span></div>
              </div>
              <div class="mock-sell-col">
                <div class="mock-price-btn"><span>100</span><span class="mock-btn-sell">Sell</span></div>
                <div class="mock-price-btn"><span>101</span><span class="mock-btn-sell">Sell</span></div>
                <div class="mock-price-btn"><span>102</span><span class="mock-btn-sell">Sell</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Caption callout -->
    <div v-if="caption" class="preview-caption">
      <p>{{ caption }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  highlight: { type: String, default: 'all' },
  caption: { type: String, default: '' },
  trend: { type: String, default: 'neutral' }, // neutral, up, down, unclear-up, unclear-down
})

const trendLines = {
  neutral:      [[10,50],[30,45],[50,40],[70,30],[90,35],[110,32],[130,38],[150,35],[170,40],[190,37]],
  up:           [[10,65],[30,60],[50,55],[70,50],[90,42],[110,35],[130,30],[150,25],[170,20],[190,15]],
  down:         [[10,15],[30,20],[50,25],[70,30],[90,38],[110,45],[130,50],[150,55],[170,60],[190,65]],
  'unclear-up': [[10,55],[30,50],[50,55],[70,45],[90,50],[110,40],[130,45],[150,35],[170,40],[190,30]],
  'unclear-down':[[10,25],[30,30],[50,25],[70,35],[90,30],[110,40],[130,35],[150,45],[170,40],[190,50]],
}

const pricePoints = computed(() => trendLines[props.trend] || trendLines.neutral)
const pricePolyline = computed(() => pricePoints.value.map(p => p.join(',')).join(' '))
</script>

<style scoped>
.preview-wrapper {
  position: relative;
  margin: 1rem 0;
}

.preview-frame {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg-page);
  font-family: var(--font-mono);
  font-size: 10px;
}

/* Mock Header */
.mock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  transition: filter 0.2s, opacity 0.2s;
}

.mock-title {
  font-family: var(--font-family);
  font-weight: 700;
  font-size: 12px;
}

.mock-stats {
  display: flex;
  gap: 10px;
  font-size: 9px;
  align-items: center;
}

.mock-timer {
  font-weight: 700;
  font-size: 14px;
}

/* Mock Grid */
.mock-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1px;
  background: var(--color-border);
}

.mock-panel {
  background: var(--color-bg-surface);
  padding: 8px;
  min-height: 100px;
  transition: filter 0.2s, opacity 0.2s;
}

.mock-panel-title {
  font-family: var(--font-family);
  font-weight: 600;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--color-border);
}

.mock-panel-body {
  font-size: 9px;
}

/* Highlight / Dim */
.dimmed {
  filter: blur(2px);
  opacity: 0.4;
}

.highlighted {
  filter: none;
  opacity: 1;
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
  z-index: 1;
  position: relative;
}

.no-highlight .mock-panel,
.no-highlight .mock-header {
  filter: none;
  opacity: 1;
}

/* Caption */
.preview-caption {
  margin-top: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-family);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.preview-caption p {
  margin: 0;
}

/* Mock data styling */
.bid-color { color: var(--color-bid); }
.ask-color { color: var(--color-ask); }
.bid-border { border-left: 2px solid var(--color-bid); padding-left: 4px; }
.ask-border { border-left: 2px solid var(--color-ask); padding-left: 4px; }

.mock-vwap {
  display: flex;
  gap: 6px;
  padding: 3px 0;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--color-border);
  font-size: 8px;
}

.mock-trades-columns {
  display: flex;
  gap: 6px;
}

.mock-trades-col {
  flex: 1;
}

.mock-trade-row {
  padding: 2px 4px;
  margin-bottom: 1px;
}

.mock-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.mock-bar-group {
  display: inline-flex;
  gap: 2px;
  align-items: flex-end;
  height: 60px;
}

.mock-chart {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 8px;
  height: 70px;
  padding-bottom: 14px;
  position: relative;
}

.mock-bar {
  width: 12px;
  border-radius: 1px 1px 0 0;
}

.bid-bar { background: rgba(37, 99, 235, 0.5); border: 1px solid #2563EB; }
.ask-bar { background: rgba(203, 36, 49, 0.5); border: 1px solid #cb2431; }

.mock-axis {
  position: absolute;
  bottom: 0;
  font-size: 7px;
  color: var(--color-text-muted);
}

.mock-line-chart {
  padding: 4px;
}

.mock-svg {
  width: 100%;
  height: 60px;
}

.mock-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 4px;
  text-align: center;
}

.mock-info-label {
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mock-info-value {
  font-size: 14px;
  font-weight: 700;
}

.mock-tip {
  margin-top: 6px;
  font-size: 8px;
  border-top: 1px solid var(--color-border);
  padding-top: 4px;
}

.mock-tip ul {
  margin: 0;
  padding-left: 12px;
}

.mock-tip li {
  margin-bottom: 2px;
}

.mock-orders-row {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 9px;
  font-weight: 600;
}

.mock-order-btns {
  font-size: 8px;
  color: var(--color-text-muted);
}

.mock-button-grid {
  display: flex;
  gap: 8px;
}

.mock-buy-col, .mock-sell-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mock-price-btn {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 4px;
  font-size: 9px;
}

.mock-btn-buy {
  background: var(--color-bid);
  color: white;
  padding: 1px 6px;
  border-radius: 2px;
  font-size: 8px;
  font-weight: 600;
}

.mock-btn-sell {
  background: var(--color-ask);
  color: white;
  padding: 1px 6px;
  border-radius: 2px;
  font-size: 8px;
  font-weight: 600;
}
</style>
