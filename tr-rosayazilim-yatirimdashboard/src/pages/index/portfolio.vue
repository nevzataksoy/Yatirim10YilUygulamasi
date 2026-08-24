<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">Portföy</div>
          <div class="page-subtitle q-mt-xs">
            {{ portfolio.selectedAccount?.name || 'Yatırım hesabı' }} · varlık miktarları, ortalama
            maliyetler, güncel değer ve dağılım. Görünüm: {{ displayAsset }}.
          </div>
        </div>
        <div class="col-auto">
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
            :value="formatDisplay(totalValue)"
            icon="account_balance_wallet"
          />
        </div>
        <div class="col-12 col-sm-4">
          <MetricCard
            label="Maliyet"
            :value="formatDisplay(totalBasis)"
            icon="receipt_long"
            tone="info"
          />
        </div>
        <div class="col-12 col-sm-4">
          <MetricCard
            label="Gerçekleşmemiş K/Z"
            :value="formatDisplay(unrealizedPnl)"
            icon="show_chart"
            :tone="unrealizedPnl >= 0 ? 'positive' : 'negative'"
          />
        </div>
      </div>

      <div class="row q-col-gutter-md">
        <div v-for="item in rows" :key="item.asset" class="col-12 col-md-6 col-lg-4">
          <q-card flat class="section-card full-height">
            <q-card-section class="portfolio-card-header-section">
              <div class="portfolio-card-header">
                <AssetAvatar :asset="item.asset" size="48px" class="portfolio-card-avatar" />

                <div class="portfolio-instrument-info">
                  <div class="portfolio-instrument-name">
                    {{ item.asset }}
                  </div>

                  <div class="amount-strong portfolio-instrument-quantity">
                    {{ formatNumber(item.quantity, digitsFor(item.asset)) }} {{ item.asset }}
                  </div>
                </div>

                <div class="column items-end portfolio-market-info">
                  <div
                    v-if="item.quote"
                    class="row items-center justify-end no-wrap portfolio-last-price"
                  >
                    <span class="text-caption text-grey-6 q-mr-xs"> Son Fiyat: </span>

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
                                Son Güncelleme:
                                {{ formatDate(quoteUpdatedAt(item.quote)) }}
                              </div>
                            </div>
                          </div>
                        </div>
                      </q-menu>
                    </q-btn>
                  </div>

                  <div class="row items-center justify-end no-wrap portfolio-ratio">
                    <span class="text-caption text-grey-6 q-mr-xs"> Portföy Oranı: </span>
                    <span class="text-body2 text-weight-medium">
                      %{{ item.allocation.toFixed(1) }}
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
                  <div class="amount-primary">{{ formatDisplay(item.value) }}</div>
                </div>
                <div class="col-6">
                  <div class="text-caption text-grey-6">Maliyet</div>
                  <div class="amount-info">{{ formatDisplay(item.costBasisUsd) }}</div>
                </div>
                <div class="col-6 q-mt-sm">
                  <div class="text-caption text-grey-6">Ort. Maliyet</div>
                  <div class="amount-neutral">{{ formatDisplay(item.averageCostUsd) }}</div>
                </div>
                <div class="col-6 q-mt-sm">
                  <div class="text-caption text-grey-6">K/Z</div>
                  <div :class="item.pnl >= 0 ? 'amount-positive' : 'amount-negative'">
                    {{ formatDisplay(item.pnl) }}
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
            Önce yatırım bütçesi girişi yap; ardından alım ve dönüşüm akışını test et.
          </div>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, watch } from 'vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import MetricCard from '@/components/MetricCard.vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { useFormatters } from '@/composables/useFormatters'
import { useDisplayQuoteStore } from '@/stores/displayQuotes'
import { usePortfolioStore } from '@/stores/portfolio'

const portfolio = usePortfolioStore()
const displayQuotes = useDisplayQuoteStore()
const { formatNumber, formatDate } = useFormatters()
const { displayAsset, formatDisplay, priceUsd } = useDisplayCurrency()

const PRICE_CHANGE_FLASH_MS = 3_000
const priceChangeDirection = reactive({})
const priceChangeTimers = new Map()

const QUOTE_KEY_BY_ASSET = Object.freeze({
  BTC: 'BTC_USD',
  ETH: 'ETH_USD',
  URA: 'URA_USD',
  TRY: 'USD_TRY',
  EUR: 'EUR_USD',
})

const QUOTE_SOURCE_META = Object.freeze({
  'coinbase-spot': {
    label: 'Coinbase Spot',
    icon: 'img:https://www.coinbase.com/favicon.ico',
  },

  'coinbase-exchange-rates': {
    label: 'Coinbase Exchange Rates',
    icon: 'img:https://www.coinbase.com/favicon.ico',
  },

  'yahoo-finance': {
    label: 'Yahoo Finance',
    icon: 'img:https://s.yimg.com/rz/l/favicon.ico',
  },

  'frankfurter-central-banks': {
    label: 'Frankfurter / TCMB',
    icon: 'img:https://frankfurter.dev/favicon.ico',
  },

  'fawaz-currency-api': {
    label: 'Fawaz Currency API',
    icon: 'img:https://latest.currency-api.pages.dev/favicon.ico',
  },

  'market-snapshot': {
    label: 'Investment Engine Market Snapshot',
    icon: 'memory',
  },

  'device-cache': {
    label: 'Cihaz Önbelleği',
    icon: 'cached',
  },
})

const rows = computed(() => {
  const items = Object.values(portfolio.ledger.assets)
    .map((item) => {
      const lastPriceUsd = priceUsd(item.asset)
      const quote = quoteForAsset(item.asset)

      const value = item.quantity * lastPriceUsd

      return {
        ...item,
        value,
        pnl: value - item.costBasisUsd,
        lastPriceUsd,
        quote,
      }
    })
    .filter((item) => item.quantity > 0.0000000001)
  const total = items.reduce((sum, item) => sum + item.value, 0)
  return items
    .map((item) => ({ ...item, allocation: total > 0 ? (item.value / total) * 100 : 0 }))
    .sort((a, b) => b.value - a.value)
})

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

const totalValue = computed(() => rows.value.reduce((sum, item) => sum + item.value, 0))
const totalBasis = computed(() => rows.value.reduce((sum, item) => sum + item.costBasisUsd, 0))
const unrealizedPnl = computed(() => totalValue.value - totalBasis.value)

function digitsFor(asset) {
  if (asset === 'BTC') return 8
  if (asset === 'ETH') return 6
  if (asset === 'URA') return 4
  return 2
}

function quoteForAsset(asset) {
  const key = QUOTE_KEY_BY_ASSET[asset]

  if (!key) return null

  return displayQuotes.quotes[key] || null
}

function quoteSourceMeta(quote) {
  if (!quote) {
    return {
      label: 'Bilinmeyen kaynak',
      icon: 'source',
    }
  }

  return (
    QUOTE_SOURCE_META[quote.provider] || {
      label: quote.provider || 'Bilinmeyen kaynak',
      icon: 'source',
    }
  )
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
