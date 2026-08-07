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
            <q-card-section>
              <div class="row items-center no-wrap">
                <AssetAvatar :asset="item.asset" size="48px" />
                <div class="q-ml-md col min-width-0">
                  <div class="row items-center justify-between">
                    <div class="text-h6 text-weight-bold">{{ item.asset }}</div>
                    <q-chip dense color="grey-2" text-color="grey-9"
                      >%{{ item.allocation.toFixed(1) }}</q-chip
                    >
                  </div>
                  <div class="amount-strong q-mt-xs">
                    {{ formatNumber(item.quantity, digitsFor(item.asset)) }} {{ item.asset }}
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
import { computed } from 'vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import MetricCard from '@/components/MetricCard.vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { useFormatters } from '@/composables/useFormatters'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

const portfolio = usePortfolioStore()
const engine = useEngineStore()
const { formatNumber } = useFormatters()
const { displayAsset, formatDisplay } = useDisplayCurrency()

const rows = computed(() => {
  const items = Object.values(portfolio.ledger.assets)
    .map((item) => {
      const value = item.quantity * engine.price(item.asset)
      return { ...item, value, pnl: value - item.costBasisUsd }
    })
    .filter((item) => item.quantity > 0.0000000001)
  const total = items.reduce((sum, item) => sum + item.value, 0)
  return items
    .map((item) => ({ ...item, allocation: total > 0 ? (item.value / total) * 100 : 0 }))
    .sort((a, b) => b.value - a.value)
})

const totalValue = computed(() => rows.value.reduce((sum, item) => sum + item.value, 0))
const totalBasis = computed(() => rows.value.reduce((sum, item) => sum + item.costBasisUsd, 0))
const unrealizedPnl = computed(() => totalValue.value - totalBasis.value)

function digitsFor(asset) {
  if (asset === 'BTC') return 8
  if (asset === 'ETH') return 6
  if (asset === 'URA') return 4
  return 2
}
</script>
