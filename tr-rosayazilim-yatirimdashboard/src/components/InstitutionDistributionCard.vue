<template>
  <q-card flat class="section-card">
    <q-card-section class="row items-start justify-between q-col-gutter-md">
      <div class="col">
        <div class="text-h6 text-weight-bold">Banka / Borsa / Aracı Kurum Dağılımı</div>
        <div class="text-caption text-grey-7">
          Güncel saklama dağılımı işlem defterindeki kurum kimliğinden türetilir. Farklı varlıkların
          adetleri toplanmaz; miktarlar varlık bazında gösterilir.
        </div>
      </div>
      <div class="col-auto">
        <q-chip outline color="primary" icon="account_balance">
          {{ visibleRows.length }} kurum
        </q-chip>
      </div>
    </q-card-section>

    <q-banner v-if="dataQualityMessage" dense class="bg-orange-1 text-orange-10 q-mx-md q-mb-md" rounded>
      <template #avatar><q-icon name="warning_amber" /></template>
      {{ dataQualityMessage }}
    </q-banner>

    <q-separator />

    <q-list v-if="visibleRows.length" separator>
      <q-item v-for="row in visibleRows" :key="row.key" class="q-py-md institution-row">
        <q-item-section avatar top>
          <q-avatar color="grey-2" text-color="primary" :icon="institutionIcon(row.institutionType)" />
        </q-item-section>

        <q-item-section>
          <q-item-label class="row items-center q-gutter-sm">
            <span class="text-weight-bold">{{ row.name }}</span>
            <q-badge outline color="primary">{{ institutionTypeLabel(row) }}</q-badge>
            <q-badge v-if="row.countryCode" outline color="grey-7">{{ row.countryCode }}</q-badge>
            <q-badge v-if="row.unassigned" color="warning" text-color="black">Kurum Yok</q-badge>
          </q-item-label>

          <q-item-label caption class="q-mt-xs">
            {{ row.transactionCount }} işlem · {{ row.assets.length }} mevcut varlık
          </q-item-label>

          <div v-if="row.assets.length" class="row q-gutter-xs q-mt-sm">
            <q-chip
              v-for="asset in row.assets"
              :key="`${row.key}-${asset.asset}`"
              dense
              outline
              color="grey-7"
              size="sm"
            >
              {{ formatAssetQuantity(asset.quantity, asset.asset) }}
            </q-chip>
          </div>
          <div v-else class="text-caption text-grey-6 q-mt-sm">Güncel açık bakiye yok.</div>

          <q-linear-progress
            v-if="row.allocationPct !== null"
            rounded
            size="7px"
            :value="Math.min(1, row.allocationPct / 100)"
            color="primary"
            track-color="grey-3"
            class="q-mt-sm"
          />

          <div v-if="detailed" class="row q-col-gutter-md q-mt-xs institution-detail-grid">
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey-6">Maliyet</div>
              <div class="amount-info">{{ formatMaybe(row.costBasisDisplay) }}</div>
            </div>
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey-6">Gerçekleşmiş K/Z</div>
              <div :class="pnlClass(row.realizedPnlDisplay)">
                {{ formatMaybe(row.realizedPnlDisplay) }}
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey-6">Gerçekleşmemiş K/Z</div>
              <div :class="pnlClass(row.unrealizedPnlDisplay)">
                {{ formatMaybe(row.unrealizedPnlDisplay) }}
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey-6">Toplam K/Z</div>
              <div class="text-weight-bold" :class="pnlClass(row.totalPnlDisplay)">
                {{ formatMaybe(row.totalPnlDisplay) }}
              </div>
            </div>
          </div>
        </q-item-section>

        <q-item-section side top class="items-end institution-row__side">
          <div class="text-caption text-grey-6">Portföy Payı</div>
          <div class="text-h6 text-weight-bold">
            {{ row.allocationPct === null ? '—' : `%${formatPercent(row.allocationPct)}` }}
          </div>
          <div class="text-caption text-grey-6 q-mt-sm">Güncel Değer</div>
          <div class="amount-primary text-weight-bold">{{ formatMaybe(row.currentValueDisplay) }}</div>
        </q-item-section>
      </q-item>
    </q-list>

    <q-card-section v-else class="text-center q-pa-xl text-grey-6">
      Kurum bazında gösterilebilecek portföy bakiyesi bulunmuyor.
    </q-card-section>
  </q-card>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { useFormatters } from '@/composables/useFormatters'
import { formatAssetQuantity } from '@/services/assetFormatting'
import { buildInstitutionDistribution } from '@/services/portfolioInstitutionAnalytics'
import { useInstitutionsStore } from '@/stores/institutions'
import { usePortfolioStore } from '@/stores/portfolio'

const props = defineProps({
  detailed: { type: Boolean, default: false },
  includeClosedHistory: { type: Boolean, default: false },
})

const portfolio = usePortfolioStore()
const institutions = useInstitutionsStore()
const { formatNumber } = useFormatters()
const { displayAsset, convertUsd, formatAssetValue, priceUsd } = useDisplayCurrency()

function displayConversionAvailable() {
  return displayAsset.value === 'USD' || priceUsd(displayAsset.value) > 0
}

function historicalLedgerValue(ledger, key, usdFallback) {
  const historical = ledger?.historical?.[key]?.[displayAsset.value]
  if (historical !== null && historical !== undefined && Number.isFinite(Number(historical))) {
    return Number(historical)
  }
  if (Number(usdFallback || 0) === 0) return 0
  return displayConversionAvailable() ? convertUsd(usdFallback) : null
}

function historicalBasisDisplay(ledger) {
  let total = 0
  for (const item of Object.values(ledger?.assets || {})) {
    if (Number(item.quantity || 0) <= 0.0000000001) continue
    const historical = item.historicalCostBasis?.[displayAsset.value]
    if (historical !== null && historical !== undefined && Number.isFinite(Number(historical))) {
      total += Number(historical)
      continue
    }
    if (!displayConversionAvailable()) return null
    total += convertUsd(item.costBasisUsd)
  }
  return total
}

const rawRows = computed(() =>
  buildInstitutionDistribution({
    transactions: portfolio.selectedTransactions,
    institutions: institutions.institutions,
    priceUsd,
  }).map((row) => {
    if (!row.custodyReconciled) {
      return {
        ...row,
        currentValueDisplay: null,
        costBasisDisplay: null,
        realizedPnlDisplay: null,
        unrealizedPnlDisplay: null,
        totalPnlDisplay: null,
      }
    }

    const currentValueDisplay =
      row.valuation.currentValueUsd === null || !displayConversionAvailable()
        ? null
        : convertUsd(row.valuation.currentValueUsd)
    const costBasisDisplay = historicalBasisDisplay(row.ledger)
    const realizedPnlDisplay = historicalLedgerValue(
      row.ledger,
      'realizedPnl',
      row.valuation.realizedPnlUsd,
    )
    const unrealizedPnlDisplay =
      currentValueDisplay !== null && costBasisDisplay !== null
        ? currentValueDisplay - costBasisDisplay
        : null
    const totalPnlDisplay =
      unrealizedPnlDisplay !== null && realizedPnlDisplay !== null
        ? realizedPnlDisplay + unrealizedPnlDisplay
        : null

    return {
      ...row,
      currentValueDisplay,
      costBasisDisplay,
      realizedPnlDisplay,
      unrealizedPnlDisplay,
      totalPnlDisplay,
    }
  }),
)

const visibleRows = computed(() =>
  rawRows.value.filter((row) => props.includeClosedHistory || row.assets.length > 0),
)

const legacyTransactionCount = computed(() =>
  rawRows.value
    .filter((row) => row.legacy && !row.unassigned)
    .reduce((sum, row) => sum + row.transactionCount, 0),
)
const unassignedTransactionCount = computed(() =>
  rawRows.value
    .filter((row) => row.unassigned)
    .reduce((sum, row) => sum + row.transactionCount, 0),
)
const reconciliationIssues = computed(() => rawRows.value[0]?.reconciliationIssues || [])

const dataQualityMessage = computed(() => {
  const parts = []
  if (legacyTransactionCount.value > 0) {
    parts.push(`${legacyTransactionCount.value} işlem kurum ID yerine eski platform bilgisiyle çözümlendi`)
  }
  if (unassignedTransactionCount.value > 0) {
    parts.push(`${unassignedTransactionCount.value} işlemde kurum bilgisi yok`)
  }
  if (reconciliationIssues.value.length > 0) {
    const assets = reconciliationIssues.value.map((item) => item.asset).join(', ')
    parts.push(
      `kurum alt-ledger toplamları ana portföyle ${assets} varlıklarında mutabık değil; kurumlar arası transfer kaydı eksik olabilir`,
    )
  }
  return parts.length
    ? `${parts.join('; ')}. Güvenilir olmayan kurum yüzde/tutar/K-Z değerleri gösterilmiyor.`
    : ''
})

onMounted(async () => {
  try {
    if (!institutions.institutions.length) await institutions.sync()
  } catch {
    // İşlem satırlarının platform snapshot'ı ile dağılım yine üretilebilir.
  }
})

function institutionTypeLabel(row) {
  if (row.unassigned) return 'Belirtilmemiş'
  return institutions.typeLabel(row.institutionType)
}

function institutionIcon(type) {
  return (
    {
      BANK: 'account_balance',
      EXCHANGE: 'currency_exchange',
      BROKER: 'show_chart',
      CUSTODIAN: 'shield',
      FUND_PLATFORM: 'account_tree',
      OTHER: 'business',
    }[type] || 'business'
  )
}

function formatMaybe(value) {
  return value === null || value === undefined ? '—' : formatAssetValue(value)
}

function formatPercent(value) {
  return formatNumber(value, 1)
}

function pnlClass(value) {
  if (value === null || value === undefined) return 'amount-neutral'
  return Number(value) >= 0 ? 'amount-positive' : 'amount-negative'
}
</script>

<style scoped>
.institution-row {
  align-items: flex-start;
}

.institution-row__side {
  min-width: 150px;
}

.institution-detail-grid {
  max-width: 880px;
}

@media (max-width: 599px) {
  .institution-row {
    flex-wrap: wrap;
  }

  .institution-row__side {
    min-width: 0;
    width: 100%;
    padding-left: 58px;
    padding-top: 10px;
    align-items: flex-start;
  }
}
</style>
