<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <q-card class="transaction-revision-card">
      <q-card-section class="row items-start no-wrap">
        <div class="col min-width-0">
          <div class="row items-center q-gutter-sm">
            <div class="text-h6 text-weight-bold">İşlemi Düzenle</div>
            <q-badge outline color="primary">{{ transactionTypeLabel(type) }}</q-badge>
            <q-badge outline color="grey-7">Revizyon {{ nextRevisionNumber }}</q-badge>
          </div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Eski kayıt silinmez. Onun yerine yeni bir revizyon oluşturulur; ledger ve raporlar
            yalnız son revizyonu kullanır.
          </div>
        </div>
        <q-btn flat round dense icon="close" v-close-popup aria-label="Kapat" />
      </q-card-section>

      <q-separator />

      <q-card-section class="transaction-revision-card__body">
        <q-form
          id="transaction-revision-form"
          class="row q-col-gutter-md"
          @submit.prevent="saveRevision"
        >
          <template v-if="type === 'BUY'">
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.source_asset"
                :options="cashAssets"
                label="Alım Kaynak Varlığı"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.target_asset"
                :options="investmentAssets"
                label="Alınan Varlık"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.target_quantity"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Alım Miktarı (${form.target_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.unit_price"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Birim Fiyat (${form.source_asset}/${form.target_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.fee_amount"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Komisyon (${form.source_asset})`"
              />
            </div>
          </template>

          <template v-else-if="type === 'CONVERSION'">
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.source_asset"
                :options="conversionSourceOptions"
                label="Dönüştürülen Varlık"
              />
            </div>
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.target_asset"
                :options="conversionTargetOptions"
                label="Hedef Varlık"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.source_quantity"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Dönüştürülen Miktar (${form.source_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.pair_rate"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`${form.source_asset}/${form.target_asset} Paritesi`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.fee_asset"
                :options="conversionFeeOptions"
                label="Komisyon Varlığı"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.fee_amount"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Komisyon (${form.fee_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.target_quantity"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Gerçekleşen Net Miktar (${form.target_asset})`"
              />
            </div>
            <div v-if="conversionNeedsUsdPrice" class="col-12 col-sm-6">
              <q-input
                v-model.number="form.source_unit_price_usd"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`${form.source_asset} İşlem Fiyatı (USD)`"
              />
            </div>
          </template>

          <template v-else-if="type === 'SELL' || type === 'EXIT'">
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.source_asset"
                :options="investmentAssets"
                label="Satılan Varlık"
              />
            </div>
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.target_asset"
                :options="cashAssets"
                label="Satış Karşılığı"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.source_quantity"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Satılan Miktar (${form.source_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.unit_price"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Birim Satış Fiyatı (${form.target_asset}/${form.source_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.fee_amount"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Komisyon (${form.target_asset})`"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.net_proceeds"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Gerçekleşen Net Tutar (${form.target_asset})`"
              />
            </div>
          </template>

          <template v-else-if="type === 'CASH_IN' || type === 'CASH_OUT'">
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.cash_asset"
                :options="cashAssets"
                label="Para Birimi"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.cash_quantity"
                outlined
                type="number"
                min="0"
                step="any"
                label="Tutar"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.fee_amount"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Masraf (${form.cash_asset})`"
              />
            </div>
          </template>

          <template v-else-if="type === 'OPENING'">
            <div class="col-12 col-sm-6">
              <AppPopupSelect v-model="form.target_asset" :options="allAssets" label="Varlık" />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.target_quantity"
                outlined
                type="number"
                min="0"
                step="any"
                label="Başlangıç Miktarı"
              />
            </div>
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.price_currency"
                :options="cashAssets"
                label="Maliyet Para Birimi"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.unit_price"
                outlined
                type="number"
                min="0"
                step="any"
                label="Ortalama Maliyet / Birim Değer"
              />
            </div>
          </template>

          <div class="col-12">
            <TransactionBalanceContext
              :source-asset="preview.sourceAsset"
              :source-delta="preview.sourceDelta"
              :target-asset="preview.targetAsset"
              :target-delta="preview.targetDelta"
              :base-quantities="baseQuantities"
              :account-selectable="false"
              source-external-label="Banka / Dış Kaynak"
              target-external-label="Banka / Portföy Dışı"
            />
          </div>

          <div class="col-12 col-sm-6">
            <q-input
              v-model.number="form.usd_try"
              outlined
              type="number"
              min="0"
              step="any"
              label="USD/TRY Kuru"
            />
          </div>
          <div class="col-12 col-sm-6">
            <q-input
              v-model="form.transaction_at"
              outlined
              type="datetime-local"
              label="İşlem Tarih / Saat"
              stack-label
            />
          </div>
          <div class="col-12 col-sm-6">
            <q-input v-model.trim="form.platform" outlined label="Borsa / Platform / Banka" />
          </div>
          <div class="col-12 col-sm-6">
            <q-input
              v-model.trim="form.revision_reason"
              outlined
              label="Düzeltme Nedeni"
              hint="Audit kaydında saklanır."
            />
          </div>
          <div class="col-12">
            <q-input v-model.trim="form.note" outlined type="textarea" autogrow label="Not" />
          </div>

          <div class="col-12">
            <q-banner rounded class="surface-soft">
              <div class="row q-col-gutter-md">
                <div class="col-6 col-md-3">
                  <div class="text-caption text-grey-6">USD İşlem Karşılığı</div>
                  <div class="amount-strong">{{ formatUsd(calculated.grossUsd) }}</div>
                </div>
                <div class="col-6 col-md-3">
                  <div class="text-caption text-grey-6">Komisyon / Masraf</div>
                  <div class="amount-warning">{{ formatUsd(calculated.feeUsd) }}</div>
                </div>
                <div class="col-6 col-md-3">
                  <div class="text-caption text-grey-6">Net USD</div>
                  <div class="amount-primary">{{ formatUsd(calculated.netUsd) }}</div>
                </div>
                <div class="col-6 col-md-3">
                  <div class="text-caption text-grey-6">Revizyon</div>
                  <div class="amount-strong">
                    {{ currentRevisionNumber }} → {{ nextRevisionNumber }}
                  </div>
                </div>
              </div>
            </q-banner>
          </div>
        </q-form>
      </q-card-section>

      <q-separator />
      <q-card-actions align="right" class="popup-action-footer q-pa-md">
        <q-btn
          push
          color="grey-3"
          text-color="grey-9"
          icon="close"
          label="Vazgeç"
          no-caps
          v-close-popup
        />
        <q-btn
          push
          color="primary"
          icon="history_edu"
          label="Revizyonu Kaydet"
          no-caps
          type="submit"
          form="transaction-revision-form"
          :loading="saving"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import TransactionBalanceContext from '@/components/TransactionBalanceContext.vue'
import { useFormatters } from '@/composables/useFormatters'
import { ASSETS } from '@/services/portfolioAnalytics'
import { createTransactionRequestId } from '@/services/portfolioTransactions'
import { transactionTypeLabel } from '@/services/presentation'
import { usePortfolioStore } from '@/stores/portfolio'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  transaction: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const portfolio = usePortfolioStore()
const { formatUsd } = useFormatters()
const saving = ref(false)
const revisionRequestId = ref(createTransactionRequestId())
const cashAssets = ['TRY', 'USD']
const investmentAssets = ['BTC', 'ETH', 'URA']
const allAssets = ASSETS

const form = reactive({
  source_asset: null,
  target_asset: null,
  source_quantity: null,
  target_quantity: null,
  unit_price: null,
  pair_rate: null,
  fee_asset: null,
  fee_amount: 0,
  net_proceeds: null,
  cash_asset: 'TRY',
  cash_quantity: null,
  source_unit_price_usd: null,
  price_currency: 'USD',
  usd_try: null,
  transaction_at: '',
  platform: '',
  note: '',
  revision_reason: '',
})

const type = computed(() => props.transaction?.transaction_type || '')
const currentRevisionNumber = computed(() => portfolio.transactionRevisionNumber(props.transaction))
const nextRevisionNumber = computed(() => currentRevisionNumber.value + 1)
const baseQuantities = computed(() =>
  props.transaction ? portfolio.quantitiesWithoutTransaction(props.transaction.id) : {},
)
const conversionSourceOptions = computed(() =>
  ASSETS.filter(
    (asset) =>
      Number(baseQuantities.value[asset] || 0) > 0.0000000001 || asset === form.source_asset,
  ),
)
const conversionTargetOptions = computed(() =>
  ASSETS.filter((asset) => asset !== form.source_asset),
)
const conversionFeeOptions = computed(() => [form.source_asset, form.target_asset].filter(Boolean))
const conversionNeedsUsdPrice = computed(() => !['USD', 'TRY'].includes(form.source_asset))

function localDateTime(value) {
  const date = new Date(value || Date.now())
  if (Number.isNaN(date.getTime())) return ''
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

function initialize(tx) {
  if (!tx) return
  const metadata = tx.metadata || {}
  form.source_asset = tx.source_asset || null
  form.target_asset = tx.target_asset || null
  form.source_quantity = Number(metadata.trade_source_quantity ?? tx.source_quantity ?? 0) || null
  form.target_quantity = Number(tx.target_quantity || 0) || null
  form.unit_price = Number(metadata.entered_unit_price || 0) || null
  form.pair_rate = Number(metadata.pair_rate || 0) || null
  form.fee_asset = metadata.fee_asset || tx.target_asset || tx.source_asset || null
  form.fee_amount = Number(
    metadata.fee_source ??
      metadata.fee_target ??
      metadata.fee_quantity ??
      metadata.entered_fee_amount ??
      0,
  )
  form.net_proceeds = Number(tx.target_quantity || 0) || null
  form.cash_asset = tx.target_asset || tx.source_asset || 'TRY'
  form.cash_quantity = Number(tx.target_quantity || tx.source_quantity || 0) || null
  form.source_unit_price_usd = Number(tx.source_unit_price || 0) || null
  form.price_currency = tx.price_currency || 'USD'
  form.usd_try = Number(tx.usd_try || 0) || null
  form.transaction_at = localDateTime(tx.transaction_at)
  form.platform = tx.platform || ''
  form.note = tx.note || ''
  form.revision_reason = ''

  if (tx.transaction_type === 'BUY') {
    const fee = Number(metadata.fee_source || 0)
    const tradeCost = Number(
      metadata.trade_cost_source ?? Math.max(0, Number(tx.source_quantity || 0) - fee),
    )
    form.unit_price =
      Number(
        metadata.entered_unit_price ||
          (Number(tx.target_quantity || 0) > 0 ? tradeCost / Number(tx.target_quantity) : 0),
      ) || null
    form.fee_amount = fee
  }

  if (tx.transaction_type === 'CONVERSION') {
    form.source_quantity = Number(metadata.trade_source_quantity ?? tx.source_quantity ?? 0) || null
    form.pair_rate =
      Number(
        metadata.pair_rate ||
          (Number(form.source_quantity || 0) > 0
            ? Number(tx.target_quantity || 0) / Number(form.source_quantity)
            : 0),
      ) || null
    form.fee_asset = metadata.fee_asset || tx.target_asset || tx.source_asset
    form.fee_amount = Number(metadata.fee_quantity || 0)
  }

  if (tx.transaction_type === 'SELL' || tx.transaction_type === 'EXIT') {
    const grossTarget = Number(metadata.gross_proceeds_target || 0)
    form.unit_price =
      Number(
        metadata.entered_unit_price ||
          (Number(tx.source_quantity || 0) > 0 ? grossTarget / Number(tx.source_quantity) : 0),
      ) || null
    form.fee_amount = Number(metadata.fee_target || 0)
    form.net_proceeds = Number(tx.target_quantity || metadata.calculated_net_target || 0) || null
  }

  if (tx.transaction_type === 'OPENING') {
    form.unit_price = Number(tx.target_unit_price || 0) || null
  }
}

watch(
  () => [props.modelValue, props.transaction?.id],
  ([open]) => {
    if (open) {
      revisionRequestId.value = createTransactionRequestId()
      initialize(props.transaction)
    }
  },
  { immediate: true },
)

function assetToUsd(asset, value) {
  const amount = Number(value || 0)
  if (asset === 'USD') return amount
  if (asset === 'TRY') {
    const fx = Number(form.usd_try || 0)
    return fx > 0 ? amount / fx : 0
  }
  if (asset === form.source_asset && Number(form.source_unit_price_usd || 0) > 0) {
    return amount * Number(form.source_unit_price_usd)
  }
  if (
    asset === form.target_asset &&
    type.value === 'CONVERSION' &&
    Number(form.pair_rate || 0) > 0
  ) {
    const sourceUsd = sourceUnitPriceUsd.value
    return sourceUsd > 0 ? amount * (sourceUsd / Number(form.pair_rate)) : 0
  }
  return 0
}

const sourceUnitPriceUsd = computed(() => {
  if (form.source_asset === 'USD') return 1
  if (form.source_asset === 'TRY') {
    const fx = Number(form.usd_try || 0)
    return fx > 0 ? 1 / fx : 0
  }
  return Number(form.source_unit_price_usd || 0)
})

const calculated = computed(() => {
  if (type.value === 'BUY') {
    const tradeCost = Number(form.target_quantity || 0) * Number(form.unit_price || 0)
    const fee = Number(form.fee_amount || 0)
    return {
      tradeCost,
      sourceDebit: tradeCost + fee,
      grossUsd: assetToUsd(form.source_asset, tradeCost),
      feeUsd: assetToUsd(form.source_asset, fee),
      netUsd: assetToUsd(form.source_asset, tradeCost),
    }
  }

  if (type.value === 'CONVERSION') {
    const sourceQuantity = Number(form.source_quantity || 0)
    const feeQuantity = Number(form.fee_amount || 0)
    const sourceDebit = sourceQuantity + (form.fee_asset === form.source_asset ? feeQuantity : 0)
    const grossTarget = sourceQuantity * Number(form.pair_rate || 0)
    const feeUsd = assetToUsd(form.fee_asset, feeQuantity)
    return {
      sourceDebit,
      grossTarget,
      grossUsd: sourceQuantity * sourceUnitPriceUsd.value,
      feeUsd,
      netUsd: sourceQuantity * sourceUnitPriceUsd.value,
    }
  }

  if (type.value === 'SELL' || type.value === 'EXIT') {
    const grossTarget = Number(form.source_quantity || 0) * Number(form.unit_price || 0)
    const feeTarget = Number(form.fee_amount || 0)
    const netTarget = Number(form.net_proceeds || 0)
    return {
      grossTarget,
      grossUsd: assetToUsd(form.target_asset, grossTarget),
      feeUsd: assetToUsd(form.target_asset, feeTarget),
      netUsd: assetToUsd(form.target_asset, netTarget),
    }
  }

  if (type.value === 'CASH_IN' || type.value === 'CASH_OUT') {
    const grossUsd = assetToUsd(form.cash_asset, form.cash_quantity)
    return {
      grossUsd,
      feeUsd: assetToUsd(form.cash_asset, form.fee_amount),
      netUsd: grossUsd,
    }
  }

  if (type.value === 'OPENING') {
    const localCost = Number(form.target_quantity || 0) * Number(form.unit_price || 0)
    const grossUsd = form.price_currency === 'TRY' ? assetToUsd('TRY', localCost) : localCost
    return { grossUsd, feeUsd: 0, netUsd: grossUsd }
  }

  return { grossUsd: 0, feeUsd: 0, netUsd: 0 }
})

const preview = computed(() => {
  if (type.value === 'BUY') {
    return {
      sourceAsset: form.source_asset,
      sourceDelta: -Number(calculated.value.sourceDebit || 0),
      targetAsset: form.target_asset,
      targetDelta: Number(form.target_quantity || 0),
    }
  }
  if (type.value === 'CONVERSION') {
    return {
      sourceAsset: form.source_asset,
      sourceDelta: -Number(calculated.value.sourceDebit || 0),
      targetAsset: form.target_asset,
      targetDelta: Number(form.target_quantity || 0),
    }
  }
  if (type.value === 'SELL' || type.value === 'EXIT') {
    return {
      sourceAsset: form.source_asset,
      sourceDelta: -Number(form.source_quantity || 0),
      targetAsset: form.target_asset,
      targetDelta: Number(form.net_proceeds || 0),
    }
  }
  if (type.value === 'CASH_IN')
    return {
      sourceAsset: null,
      sourceDelta: 0,
      targetAsset: form.cash_asset,
      targetDelta: Number(form.cash_quantity || 0),
    }
  if (type.value === 'CASH_OUT')
    return {
      sourceAsset: form.cash_asset,
      sourceDelta: -Number(form.cash_quantity || 0),
      targetAsset: null,
      targetDelta: 0,
    }
  if (type.value === 'OPENING')
    return {
      sourceAsset: null,
      sourceDelta: 0,
      targetAsset: form.target_asset,
      targetDelta: Number(form.target_quantity || 0),
    }
  return { sourceAsset: null, sourceDelta: 0, targetAsset: null, targetDelta: 0 }
})

function available(asset) {
  return Number(baseQuantities.value?.[asset] || 0)
}

function validate() {
  if (!props.transaction) return 'Düzenlenecek işlem bulunamadı.'
  if (!Number(form.usd_try || 0) || Number(form.usd_try) <= 0)
    return 'USD/TRY kuru sıfırdan büyük olmalı.'

  if (type.value === 'BUY') {
    if (!form.source_asset || !form.target_asset) return 'Kaynak ve hedef varlık seçilmeli.'
    if (Number(form.target_quantity || 0) <= 0 || Number(form.unit_price || 0) <= 0)
      return 'Alım miktarı ve birim fiyat sıfırdan büyük olmalı.'
    if (Number(calculated.value.sourceDebit || 0) > available(form.source_asset) + 1e-10)
      return `${form.source_asset} bakiyesi revize işlem için yetersiz.`
  }

  if (type.value === 'CONVERSION') {
    if (!form.source_asset || !form.target_asset || form.source_asset === form.target_asset)
      return 'Kaynak ve hedef varlık farklı olmalı.'
    if (
      Number(form.source_quantity || 0) <= 0 ||
      Number(form.pair_rate || 0) <= 0 ||
      Number(form.target_quantity || 0) <= 0
    )
      return 'Miktar, parite ve net hedef sıfırdan büyük olmalı.'
    if (conversionNeedsUsdPrice.value && sourceUnitPriceUsd.value <= 0)
      return `${form.source_asset} işlem fiyatı (USD) gerekli.`
    if (Number(calculated.value.sourceDebit || 0) > available(form.source_asset) + 1e-10)
      return `${form.source_asset} bakiyesi revize işlem için yetersiz.`
  }

  if (type.value === 'SELL' || type.value === 'EXIT') {
    if (
      Number(form.source_quantity || 0) <= 0 ||
      Number(form.unit_price || 0) <= 0 ||
      Number(form.net_proceeds || 0) <= 0
    )
      return 'Satış miktarı, birim fiyat ve net tutar sıfırdan büyük olmalı.'
    if (Number(form.source_quantity || 0) > available(form.source_asset) + 1e-10)
      return `${form.source_asset} bakiyesi revize işlem için yetersiz.`
  }

  if (type.value === 'CASH_IN' || type.value === 'CASH_OUT') {
    if (!form.cash_asset || Number(form.cash_quantity || 0) <= 0)
      return 'Para birimi ve tutar gerekli.'
    if (
      type.value === 'CASH_OUT' &&
      Number(form.cash_quantity || 0) > available(form.cash_asset) + 1e-10
    )
      return `${form.cash_asset} bakiyesi revize sermaye çıkışı için yetersiz.`
  }

  if (type.value === 'OPENING') {
    if (
      !form.target_asset ||
      Number(form.target_quantity || 0) <= 0 ||
      Number(form.unit_price || 0) <= 0
    )
      return 'Başlangıç varlığı, miktarı ve maliyeti gerekli.'
  }

  return ''
}

function buildReplacement() {
  const shared = {
    transaction_at: new Date(form.transaction_at).toISOString(),
    usd_try: Number(form.usd_try),
    platform: form.platform,
    note: form.note,
  }

  if (type.value === 'BUY') {
    const tradeCost = Number(calculated.value.tradeCost || 0)
    const targetQty = Number(form.target_quantity)
    return {
      ...shared,
      transaction_type: 'BUY',
      source_asset: form.source_asset,
      target_asset: form.target_asset,
      source_quantity: Number(calculated.value.sourceDebit),
      target_quantity: targetQty,
      price_currency: form.source_asset,
      source_unit_price: 1,
      target_unit_price: targetQty > 0 ? Number(calculated.value.grossUsd) / targetQty : null,
      gross_usd: Number(calculated.value.grossUsd),
      fee_usd: Number(calculated.value.feeUsd),
      net_usd: Number(calculated.value.grossUsd),
      metadata: {
        entry_flow: 'BUY_FROM_CASH',
        entered_unit_price: Number(form.unit_price),
        entered_price_currency: form.source_asset,
        trade_cost_source: tradeCost,
        fee_source: Number(form.fee_amount || 0),
        source_balance_debit: Number(calculated.value.sourceDebit),
      },
    }
  }

  if (type.value === 'CONVERSION') {
    const sourceQty = Number(form.source_quantity)
    const targetQty = Number(form.target_quantity)
    const grossUsd = Number(calculated.value.grossUsd)
    const grossTarget = sourceQty * Number(form.pair_rate)
    return {
      ...shared,
      transaction_type: 'CONVERSION',
      source_asset: form.source_asset,
      target_asset: form.target_asset,
      source_quantity: Number(calculated.value.sourceDebit),
      target_quantity: targetQty,
      price_currency: form.target_asset,
      source_unit_price: sourceUnitPriceUsd.value,
      target_unit_price: targetQty > 0 ? grossUsd / targetQty : null,
      gross_usd: grossUsd,
      fee_usd: Number(calculated.value.feeUsd),
      net_usd: grossUsd,
      metadata: {
        entry_flow: 'PORTFOLIO_CONVERSION',
        trade_source_quantity: sourceQty,
        source_balance_debit: Number(calculated.value.sourceDebit),
        pair_rate: Number(form.pair_rate),
        calculated_gross_target: grossTarget,
        calculated_net_target:
          grossTarget - (form.fee_asset === form.target_asset ? Number(form.fee_amount || 0) : 0),
        target_manually_edited: true,
        fee_asset: form.fee_asset,
        fee_quantity: Number(form.fee_amount || 0),
      },
    }
  }

  if (type.value === 'SELL' || type.value === 'EXIT') {
    const sourceQty = Number(form.source_quantity)
    const grossUsd = Number(calculated.value.grossUsd)
    const netUsd = Number(calculated.value.netUsd)
    return {
      ...shared,
      transaction_type: type.value,
      source_asset: form.source_asset,
      target_asset: form.target_asset,
      source_quantity: sourceQty,
      target_quantity: Number(form.net_proceeds),
      price_currency: form.target_asset,
      source_unit_price: sourceQty > 0 ? grossUsd / sourceQty : null,
      target_unit_price: form.target_asset === 'USD' ? 1 : 1 / Number(form.usd_try),
      gross_usd: grossUsd,
      fee_usd: Number(calculated.value.feeUsd),
      net_usd: netUsd,
      metadata: {
        entry_flow: 'ASSET_SALE_TO_CASH',
        entered_unit_price: Number(form.unit_price),
        entered_price_currency: form.target_asset,
        gross_proceeds_target: Number(calculated.value.grossTarget),
        fee_target: Number(form.fee_amount || 0),
        calculated_net_target: Number(calculated.value.grossTarget) - Number(form.fee_amount || 0),
        net_manually_edited: true,
      },
    }
  }

  if (type.value === 'CASH_IN' || type.value === 'CASH_OUT') {
    const incoming = type.value === 'CASH_IN'
    const qty = Number(form.cash_quantity)
    const unitUsd = form.cash_asset === 'USD' ? 1 : 1 / Number(form.usd_try)
    return {
      ...shared,
      transaction_type: type.value,
      source_asset: incoming ? null : form.cash_asset,
      target_asset: incoming ? form.cash_asset : null,
      source_quantity: incoming ? null : qty,
      target_quantity: incoming ? qty : null,
      price_currency: form.cash_asset,
      source_unit_price: unitUsd,
      target_unit_price: unitUsd,
      gross_usd: Number(calculated.value.grossUsd),
      fee_usd: Number(calculated.value.feeUsd),
      net_usd: Number(calculated.value.grossUsd),
      metadata: {
        entry_flow: incoming ? 'INVESTMENT_BUDGET_TRANSFER' : 'CAPITAL_WITHDRAWAL',
        entered_fee_asset: form.cash_asset,
        entered_fee_amount: Number(form.fee_amount || 0),
      },
    }
  }

  if (type.value === 'OPENING') {
    const targetQty = Number(form.target_quantity)
    return {
      ...shared,
      transaction_type: 'OPENING',
      source_asset: null,
      target_asset: form.target_asset,
      source_quantity: null,
      target_quantity: targetQty,
      price_currency: form.price_currency,
      source_unit_price: null,
      target_unit_price: Number(form.unit_price),
      gross_usd: Number(calculated.value.grossUsd),
      fee_usd: 0,
      net_usd: Number(calculated.value.grossUsd),
      metadata: { entry_flow: 'OPENING_BALANCE' },
    }
  }

  return null
}

async function saveRevision() {
  const error = validate()
  if (error) {
    $q.notify({ type: 'warning', message: error })
    return
  }
  const replacement = buildReplacement()
  if (!replacement) return

  saving.value = true
  try {
    const saved = await portfolio.reviseTransaction(
      props.transaction.id,
      replacement,
      form.revision_reason,
      revisionRequestId.value,
    )
    $q.notify({
      type: 'positive',
      message: `Revizyon ${portfolio.transactionRevisionNumber(saved)} kaydedildi. Eski kayıt audit geçmişinde korundu.`,
    })
    emit('saved', saved)
    emit('update:modelValue', false)
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Revizyon kaydedilemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.transaction-revision-card {
  width: min(980px, calc(100vw - 48px));
  max-width: 980px;
  max-height: 92vh;
  border-radius: 22px;
}

.transaction-revision-card__body {
  max-height: calc(92vh - 176px);
  overflow-y: auto;
}

@media (max-width: 767px) {
  .transaction-revision-card {
    width: 96vw;
    max-width: 96vw;
    max-height: 94vh;
  }
}
</style>
