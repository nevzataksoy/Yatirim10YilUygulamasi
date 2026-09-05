<template>
  <q-card flat class="section-card">
    <q-card-section>
      <div class="row items-center q-col-gutter-md">
        <div class="col">
          <div class="text-h6 text-weight-bold">Dönüşüm Girişi</div>
          <div class="text-caption text-grey-7">
            Kaynak miktarı ve pariteyi gir; hedef miktar otomatik hesaplansın. Borsa kaydındaki net
            miktarı gerektiğinde elle düzeltebilirsin.
          </div>
        </div>
        <q-icon name="sync_alt" color="primary" size="32px" />
      </div>
    </q-card-section>
    <q-separator />
    <q-card-section>
      <q-banner v-if="!sourceOptions.length" rounded class="bg-orange-1 text-orange-10 q-mb-md">
        Dönüştürülebilecek bakiye yok. Önce sermaye girişi veya alım işlemi kaydet.
      </q-banner>
      <q-form class="row q-col-gutter-md" @submit.prevent="openSummary">
        <div class="col-12 col-sm-6">
          <AppPopupSelect
            v-model="form.source_asset"
            :options="sourceOptions"
            label="Dönüştürülen Varlık"
          />
        </div>
        <div class="col-12 col-sm-6">
          <AppPopupSelect
            v-model="form.target_asset"
            :options="targetOptions"
            label="Hedef Varlık"
          />
        </div>
        <div class="col-12">
          <TransactionBalanceContext
            :source-asset="form.source_asset"
            :source-delta="-sourceDebit"
            :target-asset="form.target_asset"
            :target-delta="Number(form.target_quantity || 0)"
          />
        </div>
        <div class="col-12">
          <div class="text-caption text-grey-7 q-mb-xs">Kaynak Bakiye Kullanımı</div>
          <div class="row q-gutter-sm">
            <q-btn
              v-for="pct in percentages"
              :key="pct"
              outline
              color="primary"
              size="sm"
              :label="`%${pct}`"
              no-caps
              @click="usePercentage(pct)"
            />
          </div>
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
            :hint="`1 ${form.source_asset} = ? ${form.target_asset}`"
          >
            <template #append>
              <q-btn flat dense round icon="auto_fix_high" @click="fillMarketPairRate">
                <q-tooltip>Güncel çapraz pariteyi doldur</q-tooltip>
              </q-btn>
            </template>
          </q-input>
        </div>
        <div class="col-12 col-sm-6">
          <AppPopupSelect
            v-model="form.fee_asset"
            :options="feeAssetOptions"
            label="Komisyon Varlığı"
            :searchable="false"
          />
        </div>
        <div class="col-12 col-sm-6">
          <q-input
            v-model.number="form.fee_quantity"
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
            :hint="
              targetManuallyEdited
                ? 'Manuel düzeltildi'
                : 'Parite ve komisyona göre otomatik hesaplanıyor'
            "
            @update:model-value="onTargetEdited"
          >
            <template #append>
              <q-btn
                v-if="targetManuallyEdited"
                flat
                dense
                round
                icon="restart_alt"
                @click="restoreCalculatedTarget"
              >
                <q-tooltip>Otomatik hesaplanan miktara dön</q-tooltip>
              </q-btn>
            </template>
          </q-input>
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
        <div v-if="needsSourceUsdPrice" class="col-12 col-sm-6">
          <q-input
            v-model.number="form.source_unit_price_usd"
            outlined
            type="number"
            min="0"
            step="any"
            :label="`${form.source_asset} İşlem Fiyatı (USD)`"
            hint="Geçmiş işlemde işlem anındaki USD fiyatını yaz; güncel fiyat başlangıç değeri olarak gelir."
          >
            <template #append>
              <q-btn flat dense round icon="auto_fix_high" @click="fillSourceUsdPrice" />
            </template>
          </q-input>
        </div>
        <div class="col-12 col-sm-6">
          <q-input
            v-model="form.transaction_at"
            outlined
            type="datetime-local"
            label="Dönüşüm Tarih / Saat"
            stack-label
          />
        </div>
        <div class="col-12 col-sm-6">
          <FinancialInstitutionSelect v-model="form.platform" label="Borsa / Aracı Kurum" />
        </div>
        <div class="col-12">
          <q-banner rounded class="surface-soft">
            <div class="row q-col-gutter-md">
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Kaynak Bakiye Düşüşü</div>
                <div class="amount-negative">
                  {{ formatQuantity(sourceDebit, form.source_asset) }} {{ form.source_asset }}
                </div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Hesaplanan Brüt Hedef</div>
                <div class="amount-primary">
                  {{ formatQuantity(calculatedGrossTarget, form.target_asset) }}
                  {{ form.target_asset }}
                </div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Net Hedef</div>
                <div class="amount-positive">
                  {{ formatQuantity(form.target_quantity, form.target_asset) }}
                  {{ form.target_asset }}
                </div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Kaynak Kullanımı</div>
                <div class="amount-strong">%{{ usedPct.toFixed(2) }}</div>
              </div>
            </div>
          </q-banner>
        </div>
        <div class="col-12">
          <q-input v-model.trim="form.note" outlined type="textarea" autogrow label="Not" />
        </div>
        <div class="col-12 row justify-end q-gutter-sm">
          <q-btn
            push
            color="grey-3"
            text-color="grey-9"
            icon="arrow_back"
            label="Geçmişe Dön"
            to="/transactions"
            no-caps
          />
          <q-btn
            push
            color="primary"
            type="submit"
            icon="fact_check"
            label="Özeti Göster"
            no-caps
          />
        </div>
      </q-form>
    </q-card-section>
  </q-card>
  <q-dialog v-model="summaryOpen">
    <q-card style="width: min(94vw, 700px)">
      <q-card-section>
        <div class="text-h6">Dönüşüm Özeti</div>
        <div class="text-caption text-grey-7">
          Yeni sermaye oluşmaz; seçili hesaptaki kaynak maliyet bazı net hedef varlığa taşınır.
        </div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <TransactionBalanceContext
          compact
          :source-asset="form.source_asset"
          :source-delta="-sourceDebit"
          :target-asset="form.target_asset"
          :target-delta="Number(form.target_quantity || 0)"
        />
      </q-card-section>
      <q-list separator>
        <q-item>
          <q-item-section>İşlem</q-item-section>
          <q-item-section side>{{ form.source_asset }} → {{ form.target_asset }}</q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Dönüştürülen Miktar</q-item-section>
          <q-item-section side class="amount-negative">
            {{ formatQuantity(form.source_quantity, form.source_asset) }} {{ form.source_asset }}
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Parite</q-item-section>
          <q-item-section side>
            1 {{ form.source_asset }} = {{ formatNumber(form.pair_rate, 8) }}
            {{ form.target_asset }}
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Komisyon</q-item-section>
          <q-item-section side>
            {{ formatQuantity(form.fee_quantity, form.fee_asset) }} {{ form.fee_asset }}
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Net Alınan</q-item-section>
          <q-item-section side class="amount-positive">
            {{ formatQuantity(form.target_quantity, form.target_asset) }} {{ form.target_asset }}
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section>USD İşlem Karşılığı</q-item-section>
          <q-item-section side class="amount-strong">{{ formatUsd(grossUsd) }}</q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Kurum</q-item-section>
          <q-item-section side>{{ form.platform || '—' }}</q-item-section>
        </q-item>
        <q-item>
          <q-item-section>USD/TRY</q-item-section>
          <q-item-section side>{{ Number(form.usd_try || 0).toFixed(4) }}</q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Tarih / Saat</q-item-section>
          <q-item-section side>{{ formatDate(form.transaction_at) }}</q-item-section>
        </q-item>
      </q-list>
      <q-card-actions align="right" class="popup-action-footer q-pa-md">
        <q-btn
          push
          color="grey-3"
          text-color="grey-9"
          icon="arrow_back"
          label="Geri Dön"
          v-close-popup
          no-caps
        />
        <q-btn
          push
          color="primary"
          icon="check"
          :loading="saving"
          label="Dönüşümü Onayla"
          no-caps
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import FinancialInstitutionSelect from '@/components/FinancialInstitutionSelect.vue'
import TransactionBalanceContext from '@/components/TransactionBalanceContext.vue'
import { useFormatters } from '@/composables/useFormatters'
import { ASSETS } from '@/services/portfolioAnalytics'
import { createTransactionRequestId } from '@/services/portfolioTransactions'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'
const $q = useQuasar()
const router = useRouter()
const engine = useEngineStore()
const portfolio = usePortfolioStore()
const { formatDate, formatNumber, formatUsd } = useFormatters()
const percentages = [25, 50, 75, 100]
const saving = ref(false)
const summaryOpen = ref(false)
const targetManuallyEdited = ref(false)
const transactionRequestId = createTransactionRequestId()
const marketUsdTry = Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0)
const form = reactive({
  source_asset: 'BTC',
  target_asset: 'ETH',
  source_quantity: null,
  pair_rate: null,
  target_quantity: null,
  fee_asset: 'ETH',
  fee_quantity: 0,
  source_unit_price_usd: Number(engine.price('BTC') || 0) || null,
  usd_try: marketUsdTry || null,
  transaction_at: new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16),
  platform: '',
  note: '',
})
const sourceOptions = computed(() =>
  ASSETS.filter((asset) => Number(portfolio.quantities[asset] || 0) > 0.0000000001),
)
const targetOptions = computed(() => ASSETS.filter((asset) => asset !== form.source_asset))
const feeAssetOptions = computed(() => [form.source_asset, form.target_asset].filter(Boolean))
const availableSource = computed(() => Number(portfolio.quantities[form.source_asset] || 0))
const calculatedGrossTarget = computed(
  () => Number(form.source_quantity || 0) * Number(form.pair_rate || 0),
)
const calculatedNetTarget = computed(() =>
  Math.max(
    0,
    calculatedGrossTarget.value -
      (form.fee_asset === form.target_asset ? Number(form.fee_quantity || 0) : 0),
  ),
)
const sourceDebit = computed(
  () =>
    Number(form.source_quantity || 0) +
    (form.fee_asset === form.source_asset ? Number(form.fee_quantity || 0) : 0),
)
const needsSourceUsdPrice = computed(() => !['USD', 'TRY'].includes(form.source_asset))
const sourceUnitPriceUsd = computed(() => {
  if (form.source_asset === 'USD') return 1
  if (form.source_asset === 'TRY') {
    const fx = Number(form.usd_try || 0)
    return fx > 0 ? 1 / fx : 0
  }
  return Number(form.source_unit_price_usd || 0)
})
const grossUsd = computed(() => Number(form.source_quantity || 0) * sourceUnitPriceUsd.value)
const feeUsd = computed(() => assetAmountToUsd(form.fee_asset, Number(form.fee_quantity || 0)))
const usedPct = computed(() =>
  availableSource.value > 0 ? (sourceDebit.value / availableSource.value) * 100 : 0,
)
watch(
  sourceOptions,
  (options) => {
    if (options.length && !options.includes(form.source_asset)) form.source_asset = options[0]
  },
  { immediate: true },
)
watch(
  () => [form.source_asset, form.target_asset],
  () => {
    if (form.source_asset === form.target_asset) {
      form.target_asset = ASSETS.find((asset) => asset !== form.source_asset) || 'USD'
    }
    form.fee_asset = form.target_asset
    targetManuallyEdited.value = false
    fillSourceUsdPrice()
    fillMarketPairRate()
  },
)
watch(
  () => [form.source_quantity, form.pair_rate, form.fee_asset, form.fee_quantity],
  () => {
    if (!targetManuallyEdited.value) form.target_quantity = calculatedNetTarget.value || null
  },
)
function assetAmountToUsd(asset, value) {
  const quantity = Number(value || 0)
  if (!asset || quantity <= 0) return 0
  if (asset === 'USD') return quantity
  if (asset === 'TRY') {
    const fx = Number(form.usd_try || 0)
    return fx > 0 ? quantity / fx : 0
  }
  return quantity * Number(engine.price(asset) || 0)
}
function formatQuantity(value, asset) {
  const digits = asset === 'BTC' ? 8 : asset === 'ETH' ? 6 : asset === 'URA' ? 4 : 2
  return formatNumber(value, digits)
}
function usePercentage(pct) {
  const budget = (availableSource.value * pct) / 100
  const sourceFee = form.fee_asset === form.source_asset ? Number(form.fee_quantity || 0) : 0
  form.source_quantity = Number(Math.max(0, budget - sourceFee).toPrecision(12))
  targetManuallyEdited.value = false
  form.target_quantity = calculatedNetTarget.value || null
}
function fillSourceUsdPrice() {
  if (!needsSourceUsdPrice.value) return
  const value = Number(engine.price(form.source_asset) || 0)
  if (value > 0) form.source_unit_price_usd = value
}
function fillMarketPairRate() {
  if (!form.source_asset || !form.target_asset) return
  const sourceUsd =
    form.source_asset === 'TRY'
      ? Number(form.usd_try || 0) > 0
        ? 1 / Number(form.usd_try)
        : 0
      : form.source_asset === 'USD'
        ? 1
        : Number(engine.price(form.source_asset) || 0)
  const targetUsd =
    form.target_asset === 'TRY'
      ? Number(form.usd_try || 0) > 0
        ? 1 / Number(form.usd_try)
        : 0
      : form.target_asset === 'USD'
        ? 1
        : Number(engine.price(form.target_asset) || 0)
  if (sourceUsd > 0 && targetUsd > 0) {
    form.pair_rate = sourceUsd / targetUsd
    targetManuallyEdited.value = false
    form.target_quantity = calculatedNetTarget.value || null
  }
}
function onTargetEdited() {
  targetManuallyEdited.value = true
}
function restoreCalculatedTarget() {
  targetManuallyEdited.value = false
  form.target_quantity = calculatedNetTarget.value || null
}
function validate() {
  if (!portfolio.selectedAccountId) return 'Aktif yatırım hesabı seçili değil.'
  if (!form.source_asset || !form.target_asset || form.source_asset === form.target_asset) {
    return 'Kaynak ve hedef varlık farklı olmalı.'
  }
  if (Number(form.source_quantity || 0) <= 0) return 'Dönüştürülen miktar sıfırdan büyük olmalı.'
  if (Number(form.pair_rate || 0) <= 0) return 'Dönüşüm paritesi sıfırdan büyük olmalı.'
  if (Number(form.target_quantity || 0) <= 0) {
    return 'Gerçekleşen net hedef miktarı sıfırdan büyük olmalı.'
  }
  if (Number(form.fee_quantity || 0) < 0) return 'Komisyon negatif olamaz.'
  if (Number(form.usd_try || 0) <= 0) return 'USD/TRY kuru zorunlu.'
  if (needsSourceUsdPrice.value && sourceUnitPriceUsd.value <= 0) {
    return `${form.source_asset} işlem fiyatı (USD) gerekli.`
  }
  if (sourceDebit.value > availableSource.value + 1e-10) {
    return `${form.source_asset} bakiyesi yetersiz. Toplam düşüş ${formatQuantity(sourceDebit.value, form.source_asset)} ${form.source_asset}.`
  }
  return ''
}
function openSummary() {
  const error = validate()
  if (error) return $q.notify({ type: 'warning', message: error })
  summaryOpen.value = true
}
async function save() {
  const error = validate()
  if (error) {
    summaryOpen.value = false
    return $q.notify({ type: 'warning', message: error })
  }
  saving.value = true
  try {
    await portfolio.addTransaction({
      id: transactionRequestId,
      transaction_type: 'CONVERSION',
      source_asset: form.source_asset,
      target_asset: form.target_asset,
      source_quantity: sourceDebit.value,
      target_quantity: Number(form.target_quantity),
      price_currency: 'USD',
      source_unit_price: sourceUnitPriceUsd.value,
      target_unit_price:
        Number(form.target_quantity || 0) > 0
          ? grossUsd.value / Number(form.target_quantity)
          : null,
      usd_try: Number(form.usd_try),
      gross_usd: grossUsd.value,
      fee_usd: feeUsd.value,
      net_usd: grossUsd.value,
      platform: form.platform,
      note: form.note,
      transaction_at: new Date(form.transaction_at).toISOString(),
      metadata: {
        entry_flow: 'PORTFOLIO_CONVERSION',
        trade_source_quantity: Number(form.source_quantity),
        source_balance_debit: sourceDebit.value,
        pair_rate: Number(form.pair_rate),
        calculated_gross_target: calculatedGrossTarget.value,
        calculated_net_target: calculatedNetTarget.value,
        target_manually_edited: targetManuallyEdited.value,
        fee_asset: form.fee_asset,
        fee_quantity: Number(form.fee_quantity || 0),
        source_portfolio_pct: usedPct.value,
      },
    })
    summaryOpen.value = false
    $q.notify({ type: 'positive', message: 'Dönüşüm kaydedildi.' })
    await router.push('/transactions')
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Dönüşüm kaydedilemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>
