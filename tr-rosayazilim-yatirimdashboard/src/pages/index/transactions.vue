<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">İşlem Geçmişi</div>
          <div class="page-subtitle q-mt-xs">
            Seçili yatırım hesabındaki başlangıç, bütçe, alım, dönüşüm, satış ve sermaye çıkışları.
            Görünüm: {{ displayAsset }}.
          </div>
        </div>
        <div class="col-auto">
          <q-btn-dropdown color="primary" icon="add" label="Yeni İşlem" no-caps>
            <q-list>
              <q-item clickable v-close-popup to="/opening"
                ><q-item-section>Başlangıç Portföyü</q-item-section></q-item
              >
              <q-item clickable v-close-popup to="/cash"
                ><q-item-section>Yatırım Bütçesi / Sermaye</q-item-section></q-item
              >
              <q-item clickable v-close-popup to="/buy"
                ><q-item-section>Alım</q-item-section></q-item
              >
              <q-item clickable v-close-popup to="/conversion"
                ><q-item-section>Dönüşüm</q-item-section></q-item
              >
              <q-item clickable v-close-popup to="/sell"
                ><q-item-section>Satış</q-item-section></q-item
              >
            </q-list>
          </q-btn-dropdown>
        </div>
      </div>

      <q-card flat class="section-card q-mb-lg">
        <q-card-section class="row q-col-gutter-md items-center">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-6">Aktif Hesap</div>
            <div class="text-weight-bold">
              {{ portfolio.selectedAccount?.name || 'Yatırım Hesabı' }}
            </div>
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model.trim="search"
              outlined
              dense
              clearable
              placeholder="Varlık, platform veya not ara"
            >
              <template #prepend><q-icon name="search" /></template>
            </q-input>
          </div>
          <div class="col-6 col-md-2">
            <AppPopupSelect
              v-model="typeFilter"
              :options="typeOptions"
              label="İşlem Tipi"
              dense
              clearable
            />
          </div>
          <div class="col-6 col-md-1">
            <AppPopupSelect
              v-model="assetFilter"
              :options="assetOptions"
              label="Varlık"
              dense
              clearable
            />
          </div>
          <div class="col-12 col-md-2">
            <q-toggle
              v-model="showRevisionHistory"
              color="primary"
              label="Revizyon Geçmişi"
              dense
            />
          </div>
        </q-card-section>
      </q-card>

      <q-card flat class="section-card">
        <q-card-section class="row items-center q-pb-sm">
          <div>
            <div class="text-subtitle2 text-weight-bold">
              {{ filteredTransactions.length }} Kayıt
            </div>
            <div class="text-caption text-grey-6">
              {{ portfolio.selectedTransactions.length }} aktif işlem ·
              {{ portfolio.selectedTransactionHistory.length }} audit kaydı
            </div>
          </div>
          <q-space />
          <div class="text-caption text-grey-6">Tutarlar {{ displayAsset }} görünümünde</div>
        </q-card-section>
        <q-separator />

        <q-list separator>
          <q-item
            v-for="tx in filteredTransactions"
            :key="tx.id"
            class="q-py-md transaction-row"
            :class="{ 'transaction-row--superseded': isSuperseded(tx) }"
          >
            <q-item-section avatar>
              <q-avatar color="grey-2" text-color="primary" :icon="iconFor(tx.transaction_type)" />
            </q-item-section>

            <q-item-section>
              <q-item-label class="row items-center q-gutter-sm">
                <SemanticPill
                  :label="transactionTypeLabel(tx.transaction_type)"
                  :code="tx.transaction_type"
                  :tone="transactionTypeTone(tx.transaction_type)"
                />
                <span class="text-weight-bold">{{ describe(tx) }}</span>
                <q-badge v-if="portfolio.transactionRevisionNumber(tx) > 1" outline color="primary">
                  Revizyon {{ portfolio.transactionRevisionNumber(tx) }}
                </q-badge>
                <q-badge v-if="isSuperseded(tx)" color="grey-5" text-color="white"
                  >Eski Revizyon</q-badge
                >
                <q-badge v-if="portfolio.isCancelledTransaction(tx)" color="negative"
                  >İptal Kaydı</q-badge
                >
              </q-item-label>
              <q-item-label caption class="q-mt-xs">
                {{ formatDate(tx.transaction_at) }} · {{ tx.platform || 'Platform Yok' }}
              </q-item-label>
              <q-item-label
                v-if="tx.metadata?.revision_reason"
                caption
                class="q-mt-xs text-primary"
              >
                Düzeltme: {{ tx.metadata.revision_reason }}
              </q-item-label>
              <q-item-label v-if="tx.note" caption class="q-mt-xs">{{ tx.note }}</q-item-label>
            </q-item-section>

            <q-item-section side class="items-end q-gutter-xs transaction-row__side">
              <div :class="transactionAmountClass(tx.transaction_type)">
                {{ formatDisplay(tx.gross_usd) }}
              </div>
              <div v-if="Number(tx.fee_usd || 0)" class="text-caption amount-warning">
                Komisyon {{ formatDisplay(tx.fee_usd) }}
              </div>
              <div class="row q-gutter-xs q-mt-xs">
                <q-btn
                  v-if="isActionable(tx)"
                  push
                  round
                  dense
                  icon="edit"
                  color="primary"
                  text-color="white"
                  size="sm"
                  aria-label="İşlemi düzenle"
                  @click="editTransaction(tx)"
                  ><q-tooltip>Yeni Revizyonla Düzenle</q-tooltip></q-btn
                >
                <q-btn
                  v-if="isActionable(tx)"
                  push
                  round
                  dense
                  icon="block"
                  color="negative"
                  text-color="white"
                  size="sm"
                  class="transaction-delete-btn"
                  aria-label="İşlemi iptal et"
                  @click="openCancellation(tx)"
                  ><q-tooltip>Append-only İptal Kaydı Oluştur</q-tooltip></q-btn
                >
              </div>
            </q-item-section>
          </q-item>

          <q-item v-if="!filteredTransactions.length">
            <q-item-section class="text-center q-pa-xl text-grey-6"
              >Filtreye uygun işlem bulunamadı.</q-item-section
            >
          </q-item>
        </q-list>
      </q-card>

      <TransactionRevisionDialog
        v-model="revisionDialogOpen"
        :transaction="selectedForEdit"
        @saved="selectedForEdit = null"
      />
      <TransactionCancelDialog
        v-model="cancelDialogOpen"
        :transaction="selectedForCancel"
        @cancelled="selectedForCancel = null"
      />
    </div>
  </q-page>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import SemanticPill from '@/components/SemanticPill.vue'
import TransactionCancelDialog from '@/components/TransactionCancelDialog.vue'
import TransactionRevisionDialog from '@/components/TransactionRevisionDialog.vue'
import { useDisplayCurrency } from '@/composables/useDisplayCurrency'
import { useFormatters } from '@/composables/useFormatters'
import {
  TRANSACTION_TYPE_LABELS,
  transactionAmountClass,
  transactionTypeLabel,
  transactionTypeTone,
} from '@/services/presentation'
import { usePortfolioStore } from '@/stores/portfolio'

const portfolio = usePortfolioStore()
const { formatNumber, formatDate } = useFormatters()
const { displayAsset, formatDisplay } = useDisplayCurrency()
const search = ref('')
const typeFilter = ref(null)
const assetFilter = ref(null)
const showRevisionHistory = ref(false)
const revisionDialogOpen = ref(false)
const selectedForEdit = ref(null)
const cancelDialogOpen = ref(false)
const selectedForCancel = ref(null)

const assetOptions = ['BTC', 'ETH', 'URA', 'USD', 'TRY'].map((value) => ({ label: value, value }))
const typeOptions = Object.entries(TRANSACTION_TYPE_LABELS).map(([value, label]) => ({
  value,
  label,
  badge: value,
}))

const sourceRows = computed(() =>
  showRevisionHistory.value ? portfolio.selectedTransactionHistory : portfolio.selectedTransactions,
)

const filteredTransactions = computed(() => {
  const needle = search.value?.toLocaleLowerCase('tr-TR') || ''
  return sourceRows.value.filter((tx) => {
    if (typeFilter.value && tx.transaction_type !== typeFilter.value) return false
    if (
      assetFilter.value &&
      tx.source_asset !== assetFilter.value &&
      tx.target_asset !== assetFilter.value
    )
      return false
    if (!needle) return true
    return [
      transactionTypeLabel(tx.transaction_type),
      tx.transaction_type,
      tx.source_asset,
      tx.target_asset,
      tx.platform,
      tx.note,
      tx.metadata?.revision_reason,
      tx.metadata?.cancellation_reason,
    ]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase('tr-TR')
      .includes(needle)
  })
})

function isSuperseded(tx) {
  return portfolio.isSupersededTransaction(tx.id)
}

function isActionable(tx) {
  return !isSuperseded(tx) && !portfolio.isCancelledTransaction(tx)
}

function iconFor(type) {
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

function describe(tx) {
  if (portfolio.isCancelledTransaction(tx))
    return `İptal: ${tx.metadata?.cancellation_reason || 'Neden belirtilmedi'}`
  const source =
    tx.source_asset && tx.source_quantity
      ? `${formatNumber(tx.source_quantity, 8)} ${tx.source_asset}`
      : ''
  const target =
    tx.target_asset && tx.target_quantity
      ? `${formatNumber(tx.target_quantity, 8)} ${tx.target_asset}`
      : ''
  if (source && target) return `${source} → ${target}`
  return target || source || '—'
}

function editTransaction(tx) {
  selectedForEdit.value = tx
  revisionDialogOpen.value = true
}

function openCancellation(tx) {
  selectedForCancel.value = tx
  cancelDialogOpen.value = true
}
</script>
