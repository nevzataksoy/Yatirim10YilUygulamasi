<template>
  <q-card flat class="section-card">
    <q-card-section>
      <div class="row items-center q-col-gutter-md">
        <div class="col">
          <div class="text-h6 text-weight-bold">Satış Girişi</div>
          <div class="text-caption text-grey-7">
            Borsadaki satılan miktar, birim fiyat ve komisyonu gir; brüt/net satış tutarı ile hesap
            bakiyeleri otomatik hesaplansın.
          </div>
        </div>
        <q-icon name="sell" color="primary" size="32px" />
      </div>
    </q-card-section>

    <q-separator />

    <q-card-section>
      <q-banner v-if="!sourceOptions.length" rounded class="bg-orange-1 text-orange-10 q-mb-md">
        Satılabilecek yatırım varlığı bulunmuyor.
      </q-banner>

      <q-form class="row q-col-gutter-md" @submit.prevent="openSummary">
        <div class="col-12 col-sm-6">
          <AppPopupSelect
            v-model="form.source_asset"
            :options="sourceOptions"
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

        <div class="col-12">
          <TransactionBalanceContext
            :source-asset="form.source_asset"
            :source-delta="-Number(form.source_quantity || 0)"
            :target-asset="form.target_asset"
            :target-delta="netProceedsTarget"
          />
        </div>

        <div class="col-12">
          <div class="text-caption text-grey-7 q-mb-xs">Satış Miktarı Kolaylığı</div>
          <div class="row q-gutter-sm">
            <q-btn
              v-for="pct in [25, 50, 75, 100]"
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
          >
            <template #append>
              <q-btn flat dense round icon="auto_fix_high" @click="fillMarketPrice"
                ><q-tooltip>Güncel piyasa fiyatını doldur</q-tooltip></q-btn
              >
            </template>
          </q-input>
        </div>
        <div class="col-12 col-sm-6">
          <q-input
            v-model.number="form.fee_target"
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
            :hint="
              netManuallyEdited
                ? 'Manuel düzeltildi'
                : 'Brüt satış eksi komisyona göre otomatik hesaplanıyor'
            "
            @update:model-value="onNetEdited"
          >
            <template #append>
              <q-btn
                v-if="netManuallyEdited"
                flat
                dense
                round
                icon="restart_alt"
                @click="restoreCalculatedNet"
                ><q-tooltip>Hesaplanan net tutara dön</q-tooltip></q-btn
              >
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
        <div class="col-12 col-sm-6">
          <q-input
            v-model="form.transaction_at"
            outlined
            type="datetime-local"
            label="Satış Tarih / Saat"
            stack-label
          />
        </div>
        <div class="col-12 col-sm-6">
          <q-input v-model.trim="form.platform" outlined label="Borsa / Platform" />
        </div>

        <div class="col-12">
          <q-banner rounded class="surface-soft">
            <div class="row q-col-gutter-md">
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Brüt Satış Tutarı</div>
                <div class="amount-primary">{{ formatTarget(grossProceedsTarget) }}</div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Komisyon</div>
                <div class="amount-warning">{{ formatTarget(form.fee_target) }}</div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Net Nakit Artışı</div>
                <div class="amount-positive">{{ formatTarget(netProceedsTarget) }}</div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">USD Net Karşılığı</div>
                <div class="amount-strong">{{ formatUsd(netUsd) }}</div>
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
        <div class="text-h6">Satış Özeti</div>
        <div class="text-caption text-grey-7">
          Satış karşılığı seçili yatırım hesabında nakit olarak kalır; bankaya çekim ayrıca sermaye
          çıkışıdır.
        </div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <TransactionBalanceContext
          compact
          :source-asset="form.source_asset"
          :source-delta="-Number(form.source_quantity || 0)"
          :target-asset="form.target_asset"
          :target-delta="netProceedsTarget"
        />
      </q-card-section>
      <q-list separator>
        <q-item
          ><q-item-section>Satılan</q-item-section
          ><q-item-section side class="amount-negative"
            >{{ formatQuantity(form.source_quantity, form.source_asset) }}
            {{ form.source_asset }}</q-item-section
          ></q-item
        >
        <q-item
          ><q-item-section>Birim Fiyat</q-item-section
          ><q-item-section side
            >{{ formatTarget(form.unit_price) }} / {{ form.source_asset }}</q-item-section
          ></q-item
        >
        <q-item
          ><q-item-section>Brüt Tutar</q-item-section
          ><q-item-section side class="amount-primary">{{
            formatTarget(grossProceedsTarget)
          }}</q-item-section></q-item
        >
        <q-item
          ><q-item-section>Komisyon</q-item-section
          ><q-item-section side>{{ formatTarget(form.fee_target) }}</q-item-section></q-item
        >
        <q-item
          ><q-item-section>Net Nakit Artışı</q-item-section
          ><q-item-section side class="amount-positive">{{
            formatTarget(netProceedsTarget)
          }}</q-item-section></q-item
        >
        <q-item
          ><q-item-section>USD/TRY</q-item-section
          ><q-item-section side>{{ Number(form.usd_try || 0).toFixed(4) }}</q-item-section></q-item
        >
        <q-item
          ><q-item-section>Tarih / Saat</q-item-section
          ><q-item-section side>{{ formatDate(form.transaction_at) }}</q-item-section></q-item
        >
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
          label="Satışı Onayla"
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
import TransactionBalanceContext from '@/components/TransactionBalanceContext.vue'
import { useFormatters } from '@/composables/useFormatters'
import { createTransactionRequestId } from '@/services/portfolioTransactions'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

const $q = useQuasar()
const router = useRouter()
const engine = useEngineStore()
const portfolio = usePortfolioStore()
const { formatDate, formatNumber, formatUsd } = useFormatters()
const cashAssets = ['TRY', 'USD']
const saving = ref(false)
const summaryOpen = ref(false)
const netManuallyEdited = ref(false)
const transactionRequestId = createTransactionRequestId()
const marketUsdTry = Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0)

const form = reactive({
  source_asset: 'BTC',
  target_asset: 'TRY',
  source_quantity: null,
  unit_price: null,
  fee_target: 0,
  net_proceeds: null,
  usd_try: marketUsdTry || null,
  transaction_at: new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16),
  platform: '',
  note: '',
})

const sourceOptions = computed(() =>
  ['BTC', 'ETH', 'URA'].filter((asset) => Number(portfolio.quantities[asset] || 0) > 0.0000000001),
)
const availableSource = computed(() => Number(portfolio.quantities[form.source_asset] || 0))
const grossProceedsTarget = computed(
  () => Number(form.source_quantity || 0) * Number(form.unit_price || 0),
)
const calculatedNetProceeds = computed(() =>
  Math.max(0, grossProceedsTarget.value - Number(form.fee_target || 0)),
)
const netProceedsTarget = computed(() => Number(form.net_proceeds || 0))
const grossUsd = computed(() => targetToUsd(grossProceedsTarget.value))
const feeUsd = computed(() => targetToUsd(Number(form.fee_target || 0)))
const netUsd = computed(() => targetToUsd(netProceedsTarget.value))

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
    netManuallyEdited.value = false
    form.fee_target = 0
    fillMarketPrice()
    form.net_proceeds = calculatedNetProceeds.value || null
  },
)

watch(
  () => [form.source_quantity, form.unit_price, form.fee_target],
  () => {
    if (!netManuallyEdited.value) form.net_proceeds = calculatedNetProceeds.value || null
  },
)

function targetToUsd(value) {
  const amount = Number(value || 0)
  if (form.target_asset === 'USD') return amount
  const fx = Number(form.usd_try || 0)
  return fx > 0 ? amount / fx : 0
}

function formatQuantity(value, asset) {
  const digits = asset === 'BTC' ? 8 : asset === 'ETH' ? 6 : asset === 'URA' ? 4 : 2
  return formatNumber(value, digits)
}

function formatTarget(value) {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: form.target_asset,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function usePercentage(pct) {
  form.source_quantity = Number(((availableSource.value * pct) / 100).toPrecision(12))
  netManuallyEdited.value = false
  form.net_proceeds = calculatedNetProceeds.value || null
}

function fillMarketPrice() {
  const priceUsd = Number(engine.price(form.source_asset) || 0)
  if (priceUsd <= 0) return
  form.unit_price = form.target_asset === 'TRY' ? priceUsd * Number(form.usd_try || 0) : priceUsd
}

function onNetEdited() {
  netManuallyEdited.value = true
}
function restoreCalculatedNet() {
  netManuallyEdited.value = false
  form.net_proceeds = calculatedNetProceeds.value || null
}

function validate() {
  if (!portfolio.selectedAccountId) return 'Aktif yatırım hesabı seçili değil.'
  if (Number(form.source_quantity || 0) <= 0) return 'Satılan miktar sıfırdan büyük olmalı.'
  if (Number(form.unit_price || 0) <= 0) return 'Birim satış fiyatı sıfırdan büyük olmalı.'
  if (Number(form.fee_target || 0) < 0) return 'Komisyon negatif olamaz.'
  if (Number(form.net_proceeds || 0) <= 0)
    return 'Gerçekleşen net satış tutarı sıfırdan büyük olmalı.'
  if (Number(form.usd_try || 0) <= 0) return 'USD/TRY kuru zorunlu.'
  if (Number(form.source_quantity) > availableSource.value + 1e-10)
    return `${form.source_asset} bakiyesi yetersiz.`
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
      transaction_type: 'SELL',
      source_asset: form.source_asset,
      target_asset: form.target_asset,
      source_quantity: Number(form.source_quantity),
      target_quantity: netProceedsTarget.value,
      price_currency: form.target_asset,
      source_unit_price:
        Number(form.source_quantity || 0) > 0
          ? grossUsd.value / Number(form.source_quantity)
          : null,
      target_unit_price: form.target_asset === 'USD' ? 1 : 1 / Number(form.usd_try),
      usd_try: Number(form.usd_try),
      gross_usd: grossUsd.value,
      fee_usd: feeUsd.value,
      net_usd: netUsd.value,
      platform: form.platform,
      note: form.note,
      transaction_at: new Date(form.transaction_at).toISOString(),
      metadata: {
        entry_flow: 'ASSET_SALE_TO_CASH',
        entered_unit_price: Number(form.unit_price),
        entered_price_currency: form.target_asset,
        gross_proceeds_target: grossProceedsTarget.value,
        fee_target: Number(form.fee_target || 0),
        calculated_net_target: calculatedNetProceeds.value,
        net_manually_edited: netManuallyEdited.value,
      },
    })
    summaryOpen.value = false
    $q.notify({ type: 'positive', message: 'Satış kaydedildi; net nakit portföye eklendi.' })
    await router.push('/transactions')
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Satış kaydedilemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>
