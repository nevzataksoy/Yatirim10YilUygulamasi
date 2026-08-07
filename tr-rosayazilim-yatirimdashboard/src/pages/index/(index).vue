<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">Yatırım Görünümü</div>
          <div class="page-subtitle q-mt-xs">
            Portföy, maliyet, yatırım motoru kararları ve 10 yıllık planın tek ekranda. Görünüm:
            {{ displayAsset }}.
          </div>
        </div>
        <div class="col-auto row q-gutter-sm">
          <q-btn
            outline
            color="primary"
            icon="inventory_2"
            label="Başlangıç"
            to="/opening"
            no-caps
          />
          <q-btn color="primary" icon="add" label="Yeni İşlem" to="/buy" no-caps />
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Portföy Değeri"
            :value="formatDisplay(totalValue)"
            icon="account_balance_wallet"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Net Sermaye"
            :value="formatDisplay(portfolio.ledger.netContributedUsd)"
            icon="savings"
            tone="info"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Toplam K/Z"
            :value="formatDisplay(totalPnl)"
            :caption="`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`"
            icon="trending_up"
            :tone="totalPnl >= 0 ? 'positive' : 'negative'"
          />
        </div>
        <div class="col-12 col-sm-6 col-lg-3">
          <MetricCard
            label="Motor Durumu"
            :value="statusLabel(engineStatus)"
            :caption="
              engine.readiness?.status === 'NOT_READY'
                ? 'Gölge gözlem devam ediyor'
                : 'Model değerlendirmesi'
            "
            icon="memory"
            :tone="engineStatus === 'OK' ? 'positive' : 'warning'"
          />
        </div>
      </div>

      <div class="row q-col-gutter-lg">
        <div class="col-12 col-lg-7">
          <q-card flat class="section-card">
            <q-card-section class="row items-center">
              <div>
                <div class="text-h6 text-weight-bold">Varlık Dağılımı</div>
                <div class="text-caption text-grey-7">
                  USD bazlı değerleme korunur; ekranda {{ displayAsset }} karşılığı gösterilir.
                </div>
              </div>
              <q-space />
              <q-btn flat round icon="open_in_new" to="/portfolio"
                ><q-tooltip>Portföyü Aç</q-tooltip></q-btn
              >
            </q-card-section>
            <q-separator />
            <q-card-section>
              <div v-for="item in assetRows" :key="item.asset" class="q-py-sm">
                <div class="row items-center no-wrap">
                  <AssetAvatar :asset="item.asset" />
                  <div class="col q-ml-md min-width-0">
                    <div class="row items-center justify-between no-wrap">
                      <div>
                        <div class="text-weight-bold">{{ item.asset }}</div>
                        <div class="text-caption text-grey-6">
                          {{ formatNumber(item.quantity, item.asset === 'BTC' ? 8 : 4) }}
                        </div>
                      </div>
                      <div class="text-right">
                        <div class="amount-strong">{{ formatDisplay(item.value) }}</div>
                        <div
                          :class="item.pnl >= 0 ? 'amount-positive' : 'amount-negative'"
                          class="text-caption"
                        >
                          {{ item.pnl >= 0 ? '+' : '' }}{{ formatDisplay(item.pnl) }}
                        </div>
                      </div>
                    </div>
                    <div class="progress-track q-mt-sm">
                      <div class="progress-fill" :style="{ width: `${item.allocation}%` }" />
                    </div>
                    <div class="text-caption text-grey-6 q-mt-xs">
                      %{{ item.allocation.toFixed(1) }} portföy payı
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="!assetRows.length" class="text-center text-grey-6 q-pa-xl">
                Portföy boş. İlk adım olarak yatırım bütçesi girişi kaydet.
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-lg-5">
          <q-card flat class="section-card q-mb-lg">
            <q-card-section class="row items-center no-wrap">
              <div>
                <div class="text-h6 text-weight-bold">Son Model Kararları</div>
                <div class="text-caption text-grey-7">
                  Kararlar işlem emri değildir; karar desteği sağlar.
                </div>
              </div>
              <q-space />
              <q-btn
                flat
                round
                color="primary"
                icon="insights"
                to="/signals"
                aria-label="Sinyalleri aç"
              >
                <q-tooltip>Sinyalleri Aç</q-tooltip>
              </q-btn>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item v-for="decision in engine.decisions" :key="decision.system" class="q-py-md">
                <q-item-section>
                  <q-item-label class="row items-center q-gutter-sm">
                    <span class="text-weight-bold">{{ decision.system }}</span>
                    <SemanticPill
                      :label="statusLabel(decision.status)"
                      :code="decision.status"
                      :tone="statusTone(decision.status)"
                    />
                  </q-item-label>
                  <q-item-label caption class="q-mt-xs"
                    >{{ decision.direction }} ·
                    {{ regimeLabel(decision.regime_code) }}</q-item-label
                  >
                </q-item-section>
                <q-item-section side class="items-end">
                  <div class="text-caption text-grey-6">Avantaj</div>
                  <div class="decision-score" :class="scoreClass(decision.edge_score)">
                    {{ Number(decision.edge_score || 0).toFixed(1) }}
                  </div>
                  <div class="text-caption text-grey-6">
                    Güven {{ Number(decision.confidence || 0).toFixed(1) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <q-card flat class="section-card">
            <q-card-section class="row items-center no-wrap">
              <div>
                <div class="text-h6 text-weight-bold">Gölge Hazırlık</div>
                <div class="text-caption text-grey-7">
                  İlk canlı değerlendirmeye kadar gözlem birikimi
                </div>
              </div>
              <q-space />
              <SemanticPill
                :label="statusLabel(engine.readiness?.status || 'NOT_READY')"
                :code="engine.readiness?.status || 'NOT_READY'"
                :tone="statusTone(engine.readiness?.status || 'NOT_READY')"
              />
            </q-card-section>
            <q-separator />
            <q-card-section>
              <div v-for="item in readinessRows" :key="item.label" class="q-mb-md">
                <div class="row justify-between text-caption q-mb-xs">
                  <span>{{ item.label }}</span>
                  <span class="text-weight-bold">{{ item.value }}/{{ item.target }}</span>
                </div>
                <q-linear-progress
                  rounded
                  size="9px"
                  :value="Math.min(1, item.value / item.target)"
                  color="primary"
                  track-color="grey-3"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <q-card flat class="section-card q-mt-lg">
        <q-card-section class="row items-center no-wrap">
          <div>
            <div class="text-h6 text-weight-bold">Son İşlemler</div>
            <div class="text-caption text-grey-7">
              Seçili yatırım hesabının son portföy hareketleri
            </div>
          </div>
          <q-space />
          <q-btn
            flat
            round
            color="primary"
            icon="history"
            to="/transactions"
            aria-label="Tüm işlem geçmişi"
          >
            <q-tooltip>Tüm Geçmiş</q-tooltip>
          </q-btn>
        </q-card-section>
        <q-separator />
        <q-list separator>
          <q-item
            v-for="tx in portfolio.selectedTransactions.slice(0, 5)"
            :key="tx.id"
            class="q-py-md"
          >
            <q-item-section avatar
              ><q-avatar
                color="grey-2"
                text-color="primary"
                :icon="transactionIcon(tx.transaction_type)"
            /></q-item-section>
            <q-item-section>
              <q-item-label class="row items-center q-gutter-sm">
                <SemanticPill
                  :label="transactionTypeLabel(tx.transaction_type)"
                  :code="tx.transaction_type"
                  :tone="transactionTypeTone(tx.transaction_type)"
                />
                <span class="text-weight-bold">{{ transactionAssets(tx) }}</span>
              </q-item-label>
              <q-item-label caption class="q-mt-xs"
                >{{ formatDate(tx.transaction_at) }} ·
                {{ tx.platform || 'Platform belirtilmedi' }}</q-item-label
              >
            </q-item-section>
            <q-item-section side :class="transactionAmountClass(tx.transaction_type)">{{
              formatDisplay(tx.gross_usd)
            }}</q-item-section>
          </q-item>
          <q-item v-if="!portfolio.selectedTransactions.length"
            ><q-item-section class="text-center q-pa-xl text-grey-6"
              >Henüz işlem yok.</q-item-section
            ></q-item
          >
        </q-list>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import MetricCard from '@/components/MetricCard.vue'
import SemanticPill from '@/components/SemanticPill.vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { useFormatters } from '@/composables/useFormatters'
import {
  regimeLabel,
  statusLabel,
  statusTone,
  transactionAmountClass,
  transactionTypeLabel,
  transactionTypeTone,
} from '@/services/presentation'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

const portfolio = usePortfolioStore()
const engine = useEngineStore()
const { formatNumber, formatDate } = useFormatters()
const { displayAsset, formatDisplay } = useDisplayCurrency()

const assetRows = computed(() => {
  const rows = Object.values(portfolio.ledger.assets)
    .map((item) => {
      const value = item.quantity * engine.price(item.asset)
      return { ...item, value, pnl: value - item.costBasisUsd }
    })
    .filter((item) => item.quantity > 0.0000000001)
  const total = rows.reduce((sum, item) => sum + item.value, 0)
  return rows
    .map((item) => ({ ...item, allocation: total > 0 ? (item.value / total) * 100 : 0 }))
    .sort((a, b) => b.value - a.value)
})

const totalValue = computed(() => assetRows.value.reduce((sum, item) => sum + item.value, 0))
const totalBasis = computed(() => assetRows.value.reduce((sum, item) => sum + item.costBasisUsd, 0))
const totalPnl = computed(
  () => totalValue.value - totalBasis.value + portfolio.ledger.realizedPnlUsd,
)
const pnlPct = computed(() =>
  totalBasis.value > 0 ? (totalPnl.value / totalBasis.value) * 100 : 0,
)
const engineStatus = computed(
  () => engine.health.find((item) => item.component === 'ENGINE')?.status || 'NOT_READY',
)

const readinessRows = computed(() => {
  const stats = engine.readiness?.metrics?.stats || {}
  return [
    { label: 'Gölge Takvim Günü', value: Number(stats.calendar_days || 0), target: 30 },
    { label: 'ETH/BTC Karar Günü', value: Number(stats.crypto_decision_days || 0), target: 25 },
    { label: 'URA Karar Günü', value: Number(stats.ura_decision_days || 0), target: 20 },
    { label: 'URA Genişlik Günü', value: Number(stats.ura_breadth_dates || 0), target: 20 },
  ]
})

function scoreClass(value) {
  const score = Number(value || 0)
  if (score >= 70) return 'decision-score--high'
  if (score >= 50) return 'decision-score--mid'
  return 'decision-score--low'
}

function transactionAssets(tx) {
  const source =
    tx.source_asset && tx.source_quantity
      ? `${formatNumber(tx.source_quantity, 6)} ${tx.source_asset}`
      : ''
  const target =
    tx.target_asset && tx.target_quantity
      ? `${formatNumber(tx.target_quantity, 6)} ${tx.target_asset}`
      : ''
  if (source && target) return `${source} → ${target}`
  return target || source || '—'
}

function transactionIcon(type) {
  return (
    {
      OPENING: 'inventory_2',
      BUY: 'add_shopping_cart',
      CONVERSION: 'sync_alt',
      SELL: 'sell',
      EXIT: 'logout',
      CASH_IN: 'south_west',
      CASH_OUT: 'north_east',
    }[type] || 'swap_vert'
  )
}
</script>
