<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">Portföy</div>
          <div class="page-subtitle q-mt-xs">
            {{ portfolio.selectedAccount?.name || 'Yatırım hesabı' }} · maliyetler işlem-anı
            kurlarıyla, güncel değerler piyasa fiyatlarıyla hesaplanır. Görünüm: {{ displayAsset }}.
          </div>
        </div>
        <div class="col-12 col-md-auto row items-center q-gutter-md">
          <q-toggle
            v-model="hideZeroBalances"
            color="primary"
            label="Sıfır bakiyeli varlıkları gizle"
            dense
          />
          <q-btn
            color="primary"
            icon="inventory_2"
            label="Başlangıç Portföyü"
            to="/opening"
            no-caps
          />
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-4">
          <MetricCard
            label="Toplam Değer"
            :value="valuationComplete ? formatAssetValue(totalValueDisplay) : 'Fiyat bekleniyor'"
            icon="account_balance_wallet"
          />
        </div>
        <div class="col-12 col-sm-4">
          <MetricCard
            label="Maliyet"
            :value="formatAssetValue(totalBasisDisplay)"
            icon="receipt_long"
            tone="info"
          />
        </div>
        <div class="col-12 col-sm-4">
          <MetricCard
            label="Gerçekleşmemiş K/Z"
            :value="unrealizedPnlDisplay"
            icon="show_chart"
            :tone="unrealizedPnl === null ? 'info' : unrealizedPnl >= 0 ? 'positive' : 'negative'"
            value-tone
          />
        </div>
      </div>

      <InstitutionDistributionCard class="q-mb-lg" />

      <div class="row q-col-gutter-md">
        <div v-for="item in rows" :key="item.asset" class="col-12 col-md-6 col-lg-4">
          <q-card flat class="section-card full-height">
            <q-card-section class="portfolio-card-header-section">
              <div class="portfolio-card-header">
                <AssetAvatar
                  :asset="item.asset"
                  size="48px"
                  class="portfolio-card-avatar"
                />

                <div class="portfolio-instrument-info">
                  <div class="portfolio-instrument-name">
                    {{ item.asset }}
                  </div>

                  <div class="amount-strong portfolio-instrument-quantity">
                    {{ formatAssetQuantity(item.quantity, item.asset) }}
                  </div>
                </div>

                <div class="column items-end portfolio-market-info">
                  <div
                    v-if="item.quote"
                    class="row items-center justify-end no-wrap portfolio-last-price"
                  >
                    <span class="text-caption text-grey-6 q-mr-xs">Son Fiyat:</span>
                    <span
                      class="text-body2 text-weight-medium portfolio-last-price-value"
                      :class="lastPriceChangeClass(item.asset)"
                    >
                      {{ formatDisplay(item.lastPriceUsd) }}
                    </span>
                    <q-btn
                      flat
                      round
                      dense
                      padding="2px"
                      class="q-ml-xs provider-source-btn"
                      :aria-label="`${quoteSourceName(item.quote)} fiyat kaynağı`"
                    >
                      <q-icon
                        :name="quoteSourceIcon(item.quote)"
                        size="18px"
                        class="provider-source-icon"
                      />
                      <q-menu
                        anchor="bottom right"
                        self="top right"
                        :offset="[0, 6]"
                        class="provider-source-menu"
                      >
                        <div class="q-pa-sm">
                          <div class="row items-center no-wrap q-gutter-sm">
                            <q-icon
                              :name="quoteSourceIcon(item.quote)"
                              size="24px"
                              class="provider-source-icon"
                            />
                            <div>
                              <div class="text-body2 text-weight-medium">
                                {{ quoteSourceName(item.quote) }}
                              </div>
                              <div class="text-caption text-grey-7 q-mt-xs">
                                Son Güncelleme: {{ formatDate(quoteUpdatedAt(item.quote)) }}
                              </div>
                            </div>
                          </div>
                        </div>
                      </q-menu>
                    </q-btn>
                  </div>
                  <div v-else-if="item.quantity > POSITION_EPSILON" class="text-caption text-warning">
                    Güncel fiyat bekleniyor
                  </div>

                  <div class="row items-center justify-end no-wrap portfolio-ratio">
                    <span class="text-caption text-grey-6 q-mr-xs">Portföy Oranı:</span>
                    <span class="text-body2 text-weight-medium">
                      {{ item.valueUsd === null ? '—' : `%${item.allocation.toFixed(1)}` }}
                    </span>
                  </div>
                </div>
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section>
              <div class="row q-col-gutter-sm">
                <div class="col-6">
                  <div class="text-caption text-grey-6">Güncel Değer</div>
                  <div class="amount-primary">{{ formatMaybe(item.valueDisplay) }}</div>
                </div>
                <div class="col-6">
                  <div class="text-caption text-grey-6">Maliyet</div>
                  <div class="amount-info">{{ formatMaybe(item.basisDisplay) }}</div>
                </div>
                <div class="col-6 q-mt-sm">
                  <div class="text-caption text-grey-6">Ort. Maliyet</div>
                  <div class="amount-neutral">{{ formatMaybe(item.averageCostDisplay) }}</div>
                </div>
                <div class="col-6 q-mt-sm">
                  <div class="text-caption text-grey-6">K/Z</div>
                  <div
                    :class="
                      item.pnlDisplay === null
                        ? 'amount-neutral'
                        : item.pnlDisplay >= 0
                          ? 'amount-positive'
                          : 'amount-negative'
                    "
                  >
                    {{ formatMaybe(item.pnlDisplay) }}
                    <span class="q-ml-xs">({{ formatPnlPercent(item.pnlPercent) }})</span>
                  </div>
                </div>
              </div>
              <div class="progress-track q-mt-md">
                <div class="progress-fill" :style="{ width: `${item.allocation}%` }" />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <q-card v-if="!rows.length" flat class="section-card q-mt-lg">
        <q-card-section class="text-center q-pa-xl">
          <q-icon name="account_balance_wallet" size="54px" color="grey-4" />
          <div class="text-h6 q-mt-md">Portföy Henüz Boş</div>
          <div class="text-grey-6 q-mt-xs">
            Sıfır bakiyeli varlıkları görmek için üstteki filtreyi kapatabilir veya önce yatırım
            bütçesi girişi yapabilirsin.
          </div>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import InstitutionDistributionCard from '@/components/InstitutionDistributionCard.vue'
import MetricCard from '@/components/MetricCard.vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { useFormatters } from '@/composables/useFormatters'
import { formatAssetQuantity } from '@/services/assetFormatting'
import { TRADEABLE_ASSETS } from '@/services/portfolioAnalytics'
import { useDisplayQuoteStore } from '@/stores/displayQuotes'
import { usePortfolioStore } from '@/stores/portfolio'

const POSITION_EPSILON = 0.0000000001
const portfolio = usePortfolioStore()
const displayQuotes = useDisplayQuoteStore()
const { formatNumber, formatDate } = useFormatters()
const { displayAsset, convertUsd, formatAssetValue, formatDisplay, priceUsd } = useDisplayCurrency()
const hideZeroBalances = ref(true)

const PRICE_CHANGE_FLASH_MS = 3_000
const priceChangeDirection = reactive({})
const priceChangeTimers = new Map()

const QUOTE_KEY_BY_ASSET = Object.freeze({
  BTC: 'BTC_USD',
  ETH: 'ETH_USD',
  URA: 'URA_USD',
  TRY: 'USD_TRY',
  EUR: 'EUR_USD',
  USDT: 'USDT_USD',
  USDC: 'USDC_USD',
})

const QUOTE_SOURCE_META = Object.freeze({
  'coinbase-spot': { label: 'Coinbase Spot', icon: 'img:https://www.coinbase.com/favicon.ico' },
  'coinbase-exchange-rates': {
    label: 'Coinbase Exchange Rates',
    icon: 'img:https://www.coinbase.com/favicon.ico',
  },
  'yahoo-finance': { label: 'Yahoo Finance', icon: 'img:https://s.yimg.com/rz/l/favicon.ico' },
  'frankfurter-central-banks': {
    label: 'Frankfurter / TCMB',
    icon: 'img:https://frankfurter.dev/favicon.ico',
  },
  'fawaz-currency-api': {
    label: 'Fawaz Currency API',
    icon: 'img:https://latest.currency-api.pages.dev/favicon.ico',
  },
  'market-snapshot': { label: 'Investment Engine Market Snapshot', icon: 'memory' },
  'device-cache': { label: 'Cihaz Önbelleği', icon: 'cached' },
})

function displayConversionAvailable() {
  return displayAsset.value === 'USD' || priceUsd(displayAsset.value) > 0
}

function historicalBasisValue(item) {
  const historical = item.historicalCostBasis?.[displayAsset.value]
  if (historical !== null && historical !== undefined && Number.isFinite(Number(historical))) {
    return Number(historical)
  }
  if (item.costBasisUsd === 0) return 0
  return displayConversionAvailable() ? convertUsd(item.costBasisUsd) : null
}

const allRows = computed(() =>
  Object.values(portfolio.ledger.assets).map((item) => {
    const lastPriceUsd = priceUsd(item.asset)
    const quote = quoteForAsset(item.asset)
    const hasCurrentPrice = item.asset === 'USD' || lastPriceUsd > 0
    const valueUsd = hasCurrentPrice ? item.quantity * lastPriceUsd : null
    const valueDisplay =
      valueUsd === null || !displayConversionAvailable() ? null : convertUsd(valueUsd)
    const basisDisplay = historicalBasisValue(item)
    const averageCostDisplay =
      item.quantity > POSITION_EPSILON && basisDisplay !== null ? basisDisplay / item.quantity : 0
    const pnlDisplay =
      valueDisplay !== null && basisDisplay !== null ? valueDisplay - basisDisplay : null
    const pnlPercent =
      pnlDisplay !== null && basisDisplay > 0 ? (pnlDisplay / basisDisplay) * 100 : null

    return {
      ...item,
      valueUsd,
      valueDisplay,
      basisDisplay,
      averageCostDisplay,
      pnlDisplay,
      pnlPercent,
      lastPriceUsd,
      quote,
    }
  }),
)

const positiveRows = computed(() =>
  allRows.value.filter((item) => item.quantity > POSITION_EPSILON),
)

const totalKnownUsd = computed(() =>
  positiveRows.value.reduce((sum, item) => sum + (item.valueUsd ?? 0), 0),
)

const rows = computed(() =>
  allRows.value
    .filter((item) => {
      if (item.quantity > POSITION_EPSILON) return true
      return !hideZeroBalances.value && TRADEABLE_ASSETS.includes(item.asset)
    })
    .map((item) => ({
      ...item,
      allocation:
        item.valueUsd !== null && totalKnownUsd.value > 0
          ? (item.valueUsd / totalKnownUsd.value) * 100
          : 0,
    }))
    .sort((a, b) => (b.valueUsd ?? -1) - (a.valueUsd ?? -1)),
)

const valuationComplete = computed(
  () =>
    displayConversionAvailable() &&
    positiveRows.value.every((item) => item.valueUsd !== null && item.valueDisplay !== null),
)

const watchedLastPrices = computed(() =>
  Object.fromEntries(
    rows.value
      .filter((item) => item.quote && Number(item.lastPriceUsd) > 0)
      .map((item) => [item.asset, Number(item.lastPriceUsd)]),
  ),
)

watch(watchedLastPrices, (currentPrices, previousPrices) => {
  if (!previousPrices) return

  for (const [asset, currentPrice] of Object.entries(currentPrices)) {
    const previousPrice = Number(previousPrices[asset])
    if (
      !Number.isFinite(previousPrice) ||
      previousPrice <= 0 ||
      !Number.isFinite(currentPrice) ||
      currentPrice <= 0 ||
      currentPrice === previousPrice
    ) {
      continue
    }

    const existingTimer = priceChangeTimers.get(asset)
    if (existingTimer) clearTimeout(existingTimer)
    priceChangeDirection[asset] = currentPrice > previousPrice ? 'up' : 'down'
    const timer = setTimeout(() => {
      delete priceChangeDirection[asset]
      priceChangeTimers.delete(asset)
    }, PRICE_CHANGE_FLASH_MS)
    priceChangeTimers.set(asset, timer)
  }
})

onBeforeUnmount(() => {
  for (const timer of priceChangeTimers.values()) clearTimeout(timer)
  priceChangeTimers.clear()
})

function lastPriceChangeClass(asset) {
  return {
    'portfolio-last-price-value--up': priceChangeDirection[asset] === 'up',
    'portfolio-last-price-value--down': priceChangeDirection[asset] === 'down',
  }
}

const totalValueDisplay = computed(() =>
  positiveRows.value.reduce((sum, item) => sum + (item.valueDisplay ?? 0), 0),
)
const totalBasisDisplay = computed(() =>
  positiveRows.value.reduce((sum, item) => sum + (item.basisDisplay ?? 0), 0),
)
const unrealizedPnl = computed(() =>
  valuationComplete.value ? totalValueDisplay.value - totalBasisDisplay.value : null,
)
const unrealizedPnlPercent = computed(() =>
  unrealizedPnl.value !== null && totalBasisDisplay.value > 0
    ? (unrealizedPnl.value / totalBasisDisplay.value) * 100
    : null,
)
const unrealizedPnlDisplay = computed(() =>
  unrealizedPnl.value === null
    ? 'Fiyat bekleniyor'
    : `${formatAssetValue(unrealizedPnl.value)} (${formatPnlPercent(unrealizedPnlPercent.value)})`,
)

function formatMaybe(value) {
  return value === null || value === undefined ? '—' : formatAssetValue(value)
}

function formatPnlPercent(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  const normalized = Math.abs(number) < 0.005 ? 0 : number
  const sign = normalized > 0 ? '+' : ''
  return `${sign}${formatNumber(normalized, 2)}%`
}

function quoteForAsset(asset) {
  const key = QUOTE_KEY_BY_ASSET[asset]
  if (!key) return null
  return displayQuotes.quotes[key] || null
}

function quoteSourceMeta(quote) {
  if (!quote) return { label: 'Bilinmeyen kaynak', icon: 'source' }
  return QUOTE_SOURCE_META[quote.provider] || {
    label: quote.provider || 'Bilinmeyen kaynak',
    icon: 'source',
  }
}

function quoteSourceIcon(quote) {
  return quoteSourceMeta(quote).icon
}

function quoteSourceName(quote) {
  const source = quoteSourceMeta(quote)
  if (quote?.provider === 'market-snapshot' && quote?.upstreamProvider) {
    return `${source.label} (${quote.upstreamProvider})`
  }
  if (quote?.provider === 'device-cache' && quote?.upstreamProvider) {
    const upstream = QUOTE_SOURCE_META[quote.upstreamProvider]?.label || quote.upstreamProvider
    return `${source.label} (${upstream})`
  }
  return source.label
}

function quoteUpdatedAt(quote) {
  return quote?.fetchedAt || null
}
</script>
<style scoped>
.portfolio-card-header-section {
  padding: 16px;
}

.portfolio-card-header {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  column-gap: 12px;
  align-items: start;
}

.portfolio-card-avatar {
  align-self: start;
}

.portfolio-instrument-info {
  min-width: 0;
  padding-top: 1px;
}

.portfolio-instrument-name {
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.01em;
}

.portfolio-instrument-quantity {
  margin-top: 6px;
  line-height: 1.2;
  white-space: nowrap;
}

.portfolio-market-info {
  min-width: max-content;
  align-self: start;
  line-height: 1.2;
}

.portfolio-last-price {
  min-height: 24px;
  white-space: nowrap;
}

.portfolio-ratio {
  margin-top: 8px;
  white-space: nowrap;
}

.portfolio-last-price-value {
  transition: color 250ms ease;
}

.portfolio-last-price-value--up {
  color: var(--q-positive) !important;
  font-weight: 700 !important;
}

.portfolio-last-price-value--down {
  color: var(--q-negative) !important;
  font-weight: 700 !important;
}

.provider-source-btn {
  min-width: 24px;
  min-height: 24px;
}

.provider-source-icon {
  flex: 0 0 auto;
}

.provider-source-menu {
  min-width: 240px;
  border-radius: 10px;
}

@media (max-width: 420px) {
  .portfolio-card-header-section {
    padding: 14px;
  }

  .portfolio-card-header {
    grid-template-columns: 44px minmax(0, 1fr) auto;
    column-gap: 10px;
  }

  .portfolio-instrument-name {
    font-size: 1.05rem;
  }

  .portfolio-instrument-quantity {
    margin-top: 5px;
    font-size: 0.86rem;
  }

  .portfolio-market-info {
    font-size: 0.92rem;
  }

  .portfolio-ratio {
    margin-top: 7px;
  }
}
</style>
