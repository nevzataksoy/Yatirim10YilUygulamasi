<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">Raporlar</div>
          <div class="page-subtitle q-mt-xs">
            Sermaye, güncel portföy değeri, maliyet bazı, komisyon ve gerçekleşen/gerçekleşmemiş
            performans ayrı izlenir. Görünüm: {{ displayAsset }}.
          </div>
        </div>
        <div class="col-auto">
          <q-chip outline color="primary" icon="currency_exchange">
            Görünüm: {{ displayAsset }}
          </q-chip>
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Toplam Eklenen Sermaye"
            :value="formatAssetValue(totalAddedCapitalDisplay)"
            icon="south_west"
            tone="positive"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Toplam Çekilen Sermaye"
            :value="formatAssetValue(cashOutDisplay)"
            icon="north_east"
            tone="warning"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Net Eklenen Sermaye"
            :value="formatAssetValue(netContributedDisplay)"
            icon="savings"
            tone="info"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Güncel Portföy Değeri"
            :value="valuationComplete ? formatAssetValue(currentPortfolioValueDisplay) : 'Fiyat bekleniyor'"
            icon="account_balance_wallet"
          />
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Açık Pozisyon Maliyet Bazı"
            :value="formatAssetValue(openCostBasisDisplay)"
            icon="receipt_long"
            tone="info"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Gerçekleşmiş K/Z"
            :value="formatAssetValue(realizedPnlDisplay)"
            icon="paid"
            :tone="realizedPnlDisplay >= 0 ? 'positive' : 'negative'"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Gerçekleşmemiş K/Z"
            :value="unrealizedPnlDisplay === null ? 'Fiyat bekleniyor' : formatAssetValue(unrealizedPnlDisplay)"
            icon="show_chart"
            :tone="unrealizedPnlDisplay === null ? 'info' : unrealizedPnlDisplay >= 0 ? 'positive' : 'negative'"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Toplam K/Z"
            :value="totalPnlDisplay === null ? 'Fiyat bekleniyor' : formatAssetValue(totalPnlDisplay)"
            icon="monitoring"
            :tone="totalPnlDisplay === null ? 'info' : totalPnlDisplay >= 0 ? 'positive' : 'negative'"
          />
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Toplam Komisyon"
            :value="formatAssetValue(totalFeesDisplay)"
            icon="receipt"
            tone="warning"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Başlangıç Sermayesi"
            :value="formatAssetValue(openingCapitalDisplay)"
            icon="inventory_2"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Sonradan Eklenen Bütçe"
            :value="formatAssetValue(cashInDisplay)"
            icon="add_card"
            tone="positive"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="İşlem Sayısı"
            :value="String(portfolio.selectedTransactions.length)"
            icon="swap_vert"
            tone="info"
          />
        </div>
      </div>

      <q-card flat class="section-card q-mb-lg">
        <q-card-section>
          <div class="text-h6 text-weight-bold">Enstrüman Performansı</div>
          <div class="text-caption text-grey-7">
            BTC, ETH, URA, USDT ve USDC için pozisyon, maliyet ve K/Z ayrımı.
          </div>
        </q-card-section>
        <q-separator />
        <q-list separator>
          <q-item v-for="row in performanceRows" :key="row.asset" class="q-py-md">
            <q-item-section avatar><AssetAvatar :asset="row.asset" /></q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-bold">{{ row.asset }}</q-item-label>
              <q-item-label caption>{{ formatAssetQuantity(row.quantity, row.asset) }}</q-item-label>
              <q-item-label caption class="q-mt-xs">
                Maliyet {{ formatMaybe(row.basisDisplay) }} · Güncel {{ formatMaybe(row.currentValueDisplay) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side class="items-end">
              <div :class="row.realizedDisplay >= 0 ? 'amount-positive' : 'amount-negative'">
                Gerç. {{ formatAssetValue(row.realizedDisplay) }}
              </div>
              <div
                :class="
                  row.unrealizedDisplay === null
                    ? 'amount-neutral'
                    : row.unrealizedDisplay >= 0
                      ? 'amount-positive'
                      : 'amount-negative'
                "
              >
                Gerç. değil {{ formatMaybe(row.unrealizedDisplay) }}
              </div>
              <div
                class="text-weight-bold"
                :class="
                  row.totalPnlDisplay === null
                    ? 'amount-neutral'
                    : row.totalPnlDisplay >= 0
                      ? 'amount-positive'
                      : 'amount-negative'
                "
              >
                Toplam {{ formatMaybe(row.totalPnlDisplay) }}
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <div class="row q-col-gutter-lg">
        <div class="col-12 col-lg-7">
          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Aylık Yatırım Bütçesi</div>
              <div class="text-caption text-grey-7">
                Yalnız sermaye giriş/çıkış hareketleri gerçek yatırım bütçesini değiştirir.
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section>
              <div class="surface-soft q-pa-md q-mb-lg">
                <div class="row items-center justify-between q-col-gutter-md">
                  <div>
                    <div class="text-caption text-grey-6">Planlanan Aylık Bütçe</div>
                    <div class="text-h6 amount-primary">{{ formatDisplay(monthlyBudgetTargetUsd) }}</div>
                  </div>
                  <div class="text-right">
                    <div class="text-caption text-grey-6">Plan Girişi</div>
                    <div class="text-weight-bold">{{ budgetPlanLabel }}</div>
                  </div>
                </div>
              </div>

              <div v-for="row in monthlyBudgetRows" :key="row.month" class="q-mb-lg">
                <div class="row justify-between q-mb-xs">
                  <div>
                    <div class="text-weight-bold">{{ row.label }}</div>
                    <div class="text-caption text-grey-6">
                      Hedef {{ formatDisplay(monthlyBudgetTargetUsd) }} · Gerçekleşme %{{
                        row.completionPct.toFixed(1)
                      }}
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="amount-positive">{{ formatAssetValue(row.cashInDisplay) }}</div>
                    <div :class="row.netDisplay >= 0 ? 'amount-primary' : 'amount-negative'">
                      Net {{ formatAssetValue(row.netDisplay) }}
                    </div>
                  </div>
                </div>
                <q-linear-progress
                  rounded
                  size="10px"
                  :value="Math.min(1, row.completionPct / 100)"
                  color="primary"
                  track-color="grey-3"
                />
                <div class="row q-gutter-md text-caption q-mt-xs">
                  <span class="amount-positive">Giriş {{ formatAssetValue(row.cashInDisplay) }}</span>
                  <span class="amount-negative">Çıkış {{ formatAssetValue(row.cashOutDisplay) }}</span>
                  <span class="text-grey-6">{{ row.count }} sermaye hareketi</span>
                </div>
              </div>
              <div v-if="!monthlyBudgetRows.length" class="text-center text-grey-6 q-pa-xl">
                Henüz yatırım bütçesi transferi yok.
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-lg-5">
          <q-card flat class="section-card q-mb-lg">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Yatırım Hareketleri</div>
              <div class="text-caption text-grey-7">Alım ve dönüşüm hacmi yeni sermaye değildir.</div>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item>
                <q-item-section>
                  <q-item-label>Alım Hacmi</q-item-label>
                  <q-item-label caption>TRY/USD/USDT/USDC → alınabilir varlık</q-item-label>
                </q-item-section>
                <q-item-section side class="amount-primary">{{ formatAssetValue(buyVolumeDisplay) }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section>
                  <q-item-label>Dönüşüm Hacmi</q-item-label>
                  <q-item-label caption>Mevcut varlıklar arası</q-item-label>
                </q-item-section>
                <q-item-section side class="amount-info">{{ formatAssetValue(conversionVolumeDisplay) }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <q-card flat class="section-card q-mb-lg">
            <q-card-section><div class="text-h6 text-weight-bold">İşlem Tipi Dağılımı</div></q-card-section>
            <q-separator />
            <q-list separator>
              <q-item v-for="row in typeRows" :key="row.type">
                <q-item-section>
                  <q-item-label>
                    <SemanticPill
                      :label="transactionTypeLabel(row.type)"
                      :code="row.type"
                      :tone="transactionTypeTone(row.type)"
                    />
                  </q-item-label>
                  <q-item-label caption class="q-mt-xs">{{ row.count }} kayıt</q-item-label>
                </q-item-section>
                <q-item-section side :class="transactionAmountClass(row.type)">{{ formatAssetValue(row.volumeDisplay) }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Varlık Aktivitesi</div>
              <div class="text-caption text-grey-7">Kaynak veya hedef olarak yer aldığı işlem sayısı</div>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item v-for="row in assetActivity" :key="row.asset">
                <q-item-section avatar><AssetAvatar :asset="row.asset" /></q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-bold">{{ row.asset }}</q-item-label>
                  <q-item-label caption>{{ row.count }} işlem</q-item-label>
                </q-item-section>
                <q-item-section side class="amount-strong">{{ formatAssetValue(row.volumeDisplay) }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div>
      </div>

      <q-banner rounded class="surface-soft q-mt-lg">
        <template #avatar><q-icon name="analytics" color="primary" /></template>
        Gerçekleşmiş K/Z, kullanıcının eklediği sermayeye dahil edilmez. Portföy değerinin parçasıdır
        ve yeniden yatırıma kullanılabilir; performans raporunda ayrı tutulur.
      </q-banner>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import MetricCard from '@/components/MetricCard.vue'
import SemanticPill from '@/components/SemanticPill.vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { formatAssetQuantity } from '@/services/assetFormatting'
import { ASSETS, TRADEABLE_ASSETS } from '@/services/portfolioAnalytics'
import {
  transactionAmountClass,
  transactionTypeLabel,
  transactionTypeTone,
} from '@/services/presentation'
import { usePortfolioStore } from '@/stores/portfolio'

const POSITION_EPSILON = 0.0000000001
const portfolio = usePortfolioStore()
const { displayAsset, convertUsd, formatAssetValue, formatDisplay, historicalValue, priceUsd } =
  useDisplayCurrency()

function displayConversionAvailable() {
  return displayAsset.value === 'USD' || priceUsd(displayAsset.value) > 0
}

function ledgerHistoricalValue(key, usdFallback) {
  const historical = portfolio.ledger.historical?.[key]?.[displayAsset.value]
  if (historical !== null && historical !== undefined && Number.isFinite(Number(historical))) {
    return Number(historical)
  }
  return displayConversionAvailable() ? convertUsd(usdFallback) : 0
}

function assetHistoricalValue(item, key, usdFallback) {
  const historical = item?.[key]?.[displayAsset.value]
  if (historical !== null && historical !== undefined && Number.isFinite(Number(historical))) {
    return Number(historical)
  }
  return displayConversionAvailable() ? convertUsd(usdFallback) : null
}

const openingCapitalDisplay = computed(() =>
  ledgerHistoricalValue('openingCapital', portfolio.ledger.openingCapitalUsd),
)
const cashInDisplay = computed(() => ledgerHistoricalValue('cashIn', portfolio.ledger.cashInUsd))
const cashOutDisplay = computed(() => ledgerHistoricalValue('cashOut', portfolio.ledger.cashOutUsd))
const totalAddedCapitalDisplay = computed(() => openingCapitalDisplay.value + cashInDisplay.value)
const netContributedDisplay = computed(() =>
  ledgerHistoricalValue('netContributed', portfolio.ledger.netContributedUsd),
)
const realizedPnlDisplay = computed(() =>
  ledgerHistoricalValue('realizedPnl', portfolio.ledger.realizedPnlUsd),
)
const totalFeesDisplay = computed(() =>
  ledgerHistoricalValue('totalFees', portfolio.ledger.totalFeesUsd),
)
const buyVolumeDisplay = computed(() =>
  ledgerHistoricalValue('buyVolume', portfolio.ledger.buyVolumeUsd),
)
const conversionVolumeDisplay = computed(() =>
  ledgerHistoricalValue('conversionVolume', portfolio.ledger.conversionVolumeUsd),
)

const activeAssets = computed(() =>
  Object.values(portfolio.ledger.assets).filter((item) => item.quantity > POSITION_EPSILON),
)

const valuationComplete = computed(
  () =>
    displayConversionAvailable() &&
    activeAssets.value.every((item) => item.asset === 'USD' || priceUsd(item.asset) > 0),
)

const currentPortfolioValueDisplay = computed(() =>
  activeAssets.value.reduce((sum, item) => {
    const unitUsd = priceUsd(item.asset)
    if (!(item.asset === 'USD' || unitUsd > 0)) return sum
    return sum + convertUsd(item.quantity * unitUsd)
  }, 0),
)

const openCostBasisDisplay = computed(() =>
  activeAssets.value.reduce((sum, item) => {
    const basis = assetHistoricalValue(item, 'historicalCostBasis', item.costBasisUsd)
    return sum + Number(basis || 0)
  }, 0),
)

const unrealizedPnlDisplay = computed(() =>
  valuationComplete.value ? currentPortfolioValueDisplay.value - openCostBasisDisplay.value : null,
)
const totalPnlDisplay = computed(() =>
  unrealizedPnlDisplay.value === null ? null : realizedPnlDisplay.value + unrealizedPnlDisplay.value,
)

const performanceRows = computed(() =>
  TRADEABLE_ASSETS.map((asset) => {
    const item = portfolio.ledger.assets[asset]
    const unitUsd = priceUsd(asset)
    const currentValueDisplay =
      item && (asset === 'USD' || unitUsd > 0) && displayConversionAvailable()
        ? convertUsd(item.quantity * unitUsd)
        : item?.quantity > POSITION_EPSILON
          ? null
          : 0
    const basisDisplay = item
      ? assetHistoricalValue(item, 'historicalCostBasis', item.costBasisUsd)
      : 0
    const realizedDisplay = item
      ? assetHistoricalValue(item, 'realizedPnlHistorical', item.realizedPnlUsd) ?? 0
      : 0
    const unrealizedDisplay =
      currentValueDisplay === null || basisDisplay === null ? null : currentValueDisplay - basisDisplay
    const totalPnlDisplay =
      unrealizedDisplay === null ? null : realizedDisplay + unrealizedDisplay

    return {
      asset,
      quantity: Number(item?.quantity || 0),
      basisDisplay,
      currentValueDisplay,
      realizedDisplay,
      unrealizedDisplay,
      totalPnlDisplay,
    }
  }),
)

const monthlyBudgetTargetUsd = computed(() => Number(portfolio.settings?.monthly_budget_usd || 0))
const budgetPlanLabel = computed(() => `${formatDisplay(monthlyBudgetTargetUsd.value)} eşdeğeri`)

const monthlyBudgetRows = computed(() => {
  const grouped = new Map()
  for (const tx of portfolio.selectedTransactions) {
    if (!['CASH_IN', 'CASH_OUT'].includes(tx.transaction_type)) continue
    const date = new Date(tx.transaction_at)
    if (Number.isNaN(date.getTime())) continue
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    const row = grouped.get(key) || {
      month: key,
      label: key,
      cashInUsd: 0,
      cashOutUsd: 0,
      cashInDisplay: 0,
      cashOutDisplay: 0,
      netDisplay: 0,
      count: 0,
    }
    const grossUsd = Number(tx.gross_usd || 0)
    const grossDisplay = historicalValue(grossUsd, tx)
    if (tx.transaction_type === 'CASH_IN') {
      row.cashInUsd += grossUsd
      row.cashInDisplay += grossDisplay
    }
    if (tx.transaction_type === 'CASH_OUT') {
      row.cashOutUsd += grossUsd
      row.cashOutDisplay += grossDisplay
    }
    row.netDisplay = row.cashInDisplay - row.cashOutDisplay
    row.count += 1
    grouped.set(key, row)
  }
  return [...grouped.values()]
    .map((row) => ({
      ...row,
      completionPct:
        monthlyBudgetTargetUsd.value > 0 ? (row.cashInUsd / monthlyBudgetTargetUsd.value) * 100 : 0,
    }))
    .sort((a, b) => b.month.localeCompare(a.month))
    .slice(0, 24)
})

const typeRows = computed(() => {
  const grouped = new Map()
  for (const tx of portfolio.selectedTransactions) {
    const row = grouped.get(tx.transaction_type) || {
      type: tx.transaction_type,
      count: 0,
      volumeUsd: 0,
      volumeDisplay: 0,
    }
    const grossUsd = Number(tx.gross_usd || 0)
    row.count += 1
    row.volumeUsd += grossUsd
    row.volumeDisplay += historicalValue(grossUsd, tx)
    grouped.set(tx.transaction_type, row)
  }
  return [...grouped.values()].sort((a, b) => b.volumeUsd - a.volumeUsd)
})

const assetActivity = computed(() =>
  ASSETS.map((asset) => {
    const rows = portfolio.selectedTransactions.filter(
      (tx) => tx.source_asset === asset || tx.target_asset === asset,
    )
    return {
      asset,
      count: rows.length,
      volumeUsd: rows.reduce((sum, tx) => sum + Number(tx.gross_usd || 0), 0),
      volumeDisplay: rows.reduce(
        (sum, tx) => sum + historicalValue(Number(tx.gross_usd || 0), tx),
        0,
      ),
    }
  }).filter((row) => row.count > 0),
)

function formatMaybe(value) {
  return value === null || value === undefined ? '—' : formatAssetValue(value)
}
</script>
