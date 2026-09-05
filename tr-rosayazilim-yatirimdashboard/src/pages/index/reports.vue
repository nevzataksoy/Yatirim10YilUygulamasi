<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">Raporlar</div>
          <div class="page-subtitle q-mt-xs">
            Seçili hesaptaki yatırım bütçesi, sermaye hareketleri, maliyet ve işlem hacmi. Tutarlar
            {{ displayAsset }} cinsinde gösteriliyor.
          </div>
        </div>
        <div class="col-auto">
          <q-chip outline color="primary" icon="currency_exchange"
            >Görünüm: {{ displayAsset }}</q-chip
          >
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Başlangıç Sermayesi"
            :value="formatDisplay(portfolio.ledger.openingCapitalUsd)"
            icon="inventory_2"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Yatırım Bütçesi Girişi"
            :value="formatDisplay(portfolio.ledger.cashInUsd)"
            icon="south_west"
            tone="positive"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Sermaye Çıkışı"
            :value="formatDisplay(portfolio.ledger.cashOutUsd)"
            icon="north_east"
            tone="warning"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Net Yeni Bütçe"
            :value="formatDisplay(netBudgetUsd)"
            icon="savings"
            tone="info"
          />
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Net Sermaye"
            :value="formatDisplay(portfolio.ledger.netContributedUsd)"
            icon="account_balance_wallet"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Gerçekleşen K/Z"
            :value="formatDisplay(portfolio.ledger.realizedPnlUsd)"
            icon="paid"
            :tone="portfolio.ledger.realizedPnlUsd >= 0 ? 'positive' : 'negative'"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Komisyonlar"
            :value="formatDisplay(portfolio.ledger.totalFeesUsd)"
            icon="receipt"
            tone="warning"
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
                    <div class="text-h6 amount-primary">
                      {{ formatDisplay(monthlyBudgetTargetUsd) }}
                    </div>
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
                    <div class="amount-positive">{{ formatDisplay(row.cashIn) }}</div>
                    <div :class="row.net >= 0 ? 'amount-primary' : 'amount-negative'">
                      Net {{ formatDisplay(row.net) }}
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
                  <span class="amount-positive">Giriş {{ formatDisplay(row.cashIn) }}</span>
                  <span class="amount-negative">Çıkış {{ formatDisplay(row.cashOut) }}</span>
                  <span class="text-grey-6">{{ row.count }} sermaye hareketi</span>
                </div>
              </div>
              <div v-if="!monthlyBudgetRows.length" class="text-center text-grey-6 q-pa-xl">
                Henüz yatırım bütçesi transferi yok. İlk test adımı olarak 100.000 TRY sermaye
                girişi kaydet.
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-lg-5">
          <q-card flat class="section-card q-mb-lg">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Yatırım Hareketleri</div>
              <div class="text-caption text-grey-7">
                Alım ve dönüşüm hacmi yeni sermaye değildir.
              </div>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item>
                <q-item-section
                  ><q-item-label>Alım Hacmi</q-item-label
                  ><q-item-label caption>TRY/USD → yatırım varlığı</q-item-label></q-item-section
                >
                <q-item-section side class="amount-primary">{{
                  formatDisplay(portfolio.ledger.buyVolumeUsd)
                }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section
                  ><q-item-label>Dönüşüm Hacmi</q-item-label
                  ><q-item-label caption>Mevcut varlıklar arası</q-item-label></q-item-section
                >
                <q-item-section side class="amount-info">{{
                  formatDisplay(portfolio.ledger.conversionVolumeUsd)
                }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <q-card flat class="section-card q-mb-lg">
            <q-card-section
              ><div class="text-h6 text-weight-bold">İşlem Tipi Dağılımı</div></q-card-section
            >
            <q-separator />
            <q-list separator>
              <q-item v-for="row in typeRows" :key="row.type">
                <q-item-section>
                  <q-item-label
                    ><SemanticPill
                      :label="transactionTypeLabel(row.type)"
                      :code="row.type"
                      :tone="transactionTypeTone(row.type)"
                  /></q-item-label>
                  <q-item-label caption class="q-mt-xs">{{ row.count }} kayıt</q-item-label>
                </q-item-section>
                <q-item-section side :class="transactionAmountClass(row.type)">{{
                  formatDisplay(row.volume)
                }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Varlık Aktivitesi</div>
              <div class="text-caption text-grey-7">
                Kaynak veya hedef olarak yer aldığı işlem sayısı
              </div>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item v-for="row in assetActivity" :key="row.asset">
                <q-item-section avatar><AssetAvatar :asset="row.asset" /></q-item-section>
                <q-item-section
                  ><q-item-label class="text-weight-bold">{{ row.asset }}</q-item-label
                  ><q-item-label caption>{{ row.count }} işlem</q-item-label></q-item-section
                >
                <q-item-section side class="amount-strong">{{
                  formatDisplay(row.volume)
                }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div>
      </div>

      <q-banner rounded class="surface-soft q-mt-lg">
        <template #avatar><q-icon name="analytics" color="primary" /></template>
        Görüntüleme birimi yalnız sunumu değiştirir; muhasebe defteri USD normalize maliyet bazını
        korur.
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
import { ASSETS } from '@/services/portfolioAnalytics'
import {
  transactionAmountClass,
  transactionTypeLabel,
  transactionTypeTone,
} from '@/services/presentation'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

const portfolio = usePortfolioStore()
const engine = useEngineStore()
const { displayAsset, formatDisplay } = useDisplayCurrency()

const monthlyBudgetTargetUsd = computed(() => {
  const settings = portfolio.settings || {}
  const amount = Number(settings.monthly_budget_amount || 0)
  const currency = settings.monthly_budget_currency
  if (amount > 0 && currency === 'USD') return amount
  if (amount > 0 && currency === 'TRY') {
    const fx = Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0)
    if (fx > 0) return amount / fx
  }
  return Number(settings.monthly_budget_usd || 0)
})

const budgetPlanLabel = computed(() => {
  const settings = portfolio.settings || {}
  const amount = Number(settings.monthly_budget_amount || 0)
  const currency = settings.monthly_budget_currency
  if (amount > 0 && currency) {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount)
  }
  return `${formatDisplay(monthlyBudgetTargetUsd.value)} eşdeğeri`
})

const netBudgetUsd = computed(() => portfolio.ledger.cashInUsd - portfolio.ledger.cashOutUsd)

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
      cashIn: 0,
      cashOut: 0,
      net: 0,
      count: 0,
    }
    const gross = Number(tx.gross_usd || 0)
    if (tx.transaction_type === 'CASH_IN') row.cashIn += gross
    if (tx.transaction_type === 'CASH_OUT') row.cashOut += gross
    row.net = row.cashIn - row.cashOut
    row.count += 1
    grouped.set(key, row)
  }
  return [...grouped.values()]
    .map((row) => ({
      ...row,
      completionPct:
        monthlyBudgetTargetUsd.value > 0 ? (row.cashIn / monthlyBudgetTargetUsd.value) * 100 : 0,
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
      volume: 0,
    }
    row.count += 1
    row.volume += Number(tx.gross_usd || 0)
    grouped.set(tx.transaction_type, row)
  }
  return [...grouped.values()].sort((a, b) => b.volume - a.volume)
})

const assetActivity = computed(() =>
  ASSETS.map((asset) => {
    const rows = portfolio.selectedTransactions.filter(
      (tx) => tx.source_asset === asset || tx.target_asset === asset,
    )
    return {
      asset,
      count: rows.length,
      volume: rows.reduce((sum, tx) => sum + Number(tx.gross_usd || 0), 0),
    }
  }).filter((row) => row.count > 0),
)
</script>
