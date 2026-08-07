<template>
  <q-card flat class="section-card">
    <q-card-section>
      <div class="row items-center q-col-gutter-md">
        <div class="col">
          <div class="text-h6 text-weight-bold">Alım Girişi</div>
          <div class="text-caption text-grey-7">
            Borsadaki işlem detayında gördüğün miktar, birim fiyat ve komisyonu gir; bakiye etkisi
            anlık hesaplanır.
          </div>
        </div>
        <q-icon name="add_shopping_cart" color="primary" size="32px" />
      </div>
    </q-card-section>

    <q-separator />

    <q-card-section>
      <q-form class="row q-col-gutter-md" @submit.prevent="openSummary">
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

        <div class="col-12">
          <TransactionBalanceContext
            :source-asset="form.source_asset"
            :source-delta="-sourceDebit"
            :target-asset="form.target_asset"
            :target-delta="Number(form.target_quantity || 0)"
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
            v-model.number="form.fee_source"
            outlined
            type="number"
            min="0"
            step="any"
            :label="`Komisyon (${form.source_asset})`"
            hint="Borsanın kaynak bakiyeden kestiği gerçek komisyonu gir."
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
            label="Alım Tarih / Saat"
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
                <div class="text-caption text-grey-6">İşlem Tutarı</div>
                <div class="amount-primary">{{ formatSource(tradeCostSource) }}</div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Toplam Kaynak Düşüşü</div>
                <div class="amount-negative">{{ formatSource(sourceDebit) }}</div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">USD Karşılığı</div>
                <div class="amount-strong">{{ formatUsd(grossUsd) }}</div>
              </div>
              <div class="col-6 col-md-3">
                <div class="text-caption text-grey-6">Kalan Kaynak</div>
                <div class="amount-positive">
                  {{ formatQuantity(remainingSource, form.source_asset) }} {{ form.source_asset }}
                </div>
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
    <q-card style="width: min(94vw, 680px)">
      <q-card-section>
        <div class="text-h6">Alım Özeti</div>
        <div class="text-caption text-grey-7">
          Kaydetmeden önce işlem ve bakiye değişimini borsa kaydıyla karşılaştır.
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
        <q-item
          ><q-item-section>Alım Miktarı</q-item-section
          ><q-item-section side class="amount-positive"
            >{{ formatQuantity(form.target_quantity, form.target_asset) }}
            {{ form.target_asset }}</q-item-section
          ></q-item
        >
        <q-item
          ><q-item-section>Birim Fiyat</q-item-section
          ><q-item-section side
            >{{ formatSource(form.unit_price) }} / {{ form.target_asset }}</q-item-section
          ></q-item
        >
        <q-item
          ><q-item-section>İşlem Tutarı</q-item-section
          ><q-item-section side class="amount-primary">{{
            formatSource(tradeCostSource)
          }}</q-item-section></q-item
        >
        <q-item
          ><q-item-section>Komisyon</q-item-section
          ><q-item-section side>{{ formatSource(form.fee_source) }}</q-item-section></q-item
        >
        <q-item
          ><q-item-section>Toplam Kaynak Düşüşü</q-item-section
          ><q-item-section side class="amount-negative">{{
            formatSource(sourceDebit)
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
          label="Alımı Onayla"
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
const investmentAssets = ['BTC', 'ETH', 'URA']
const saving = ref(false)
const summaryOpen = ref(false)
const transactionRequestId = createTransactionRequestId()
const marketUsdTry = Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0)

const form = reactive({
  source_asset: 'TRY',
  target_asset: 'BTC',
  target_quantity: null,
  unit_price: null,
  fee_source: 0,
  usd_try: marketUsdTry || null,
  transaction_at: new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16),
  platform: '',
  note: '',
})

const availableSource = computed(() => Number(portfolio.quantities[form.source_asset] || 0))
const tradeCostSource = computed(
  () => Number(form.target_quantity || 0) * Number(form.unit_price || 0),
)
const sourceDebit = computed(() => tradeCostSource.value + Number(form.fee_source || 0))
const grossUsd = computed(() => sourceToUsd(tradeCostSource.value))
const feeUsd = computed(() => sourceToUsd(Number(form.fee_source || 0)))
const unitPriceUsd = computed(() =>
  Number(form.target_quantity || 0) > 0 ? grossUsd.value / Number(form.target_quantity) : 0,
)
const remainingSource = computed(() => availableSource.value - sourceDebit.value)

watch(
  () => [form.source_asset, form.target_asset],
  () => {
    form.fee_source = 0
    fillMarketPrice()
  },
)

function sourceToUsd(value) {
  const amount = Number(value || 0)
  if (form.source_asset === 'USD') return amount
  const fx = Number(form.usd_try || 0)
  return fx > 0 ? amount / fx : 0
}

function formatQuantity(value, asset) {
  const digits = asset === 'BTC' ? 8 : asset === 'ETH' ? 6 : asset === 'URA' ? 4 : 2
  return formatNumber(value, digits)
}

function formatSource(value) {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: form.source_asset,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function fillMarketPrice() {
  const priceUsd = Number(engine.price(form.target_asset) || 0)
  if (priceUsd <= 0) return
  form.unit_price = form.source_asset === 'TRY' ? priceUsd * Number(form.usd_try || 0) : priceUsd
}

function validate() {
  if (!portfolio.selectedAccountId) return 'Aktif yatırım hesabı seçili değil.'
  if (Number(form.target_quantity || 0) <= 0) return 'Alım miktarı sıfırdan büyük olmalı.'
  if (Number(form.unit_price || 0) <= 0) return 'Birim fiyat sıfırdan büyük olmalı.'
  if (Number(form.fee_source || 0) < 0) return 'Komisyon negatif olamaz.'
  if (Number(form.usd_try || 0) <= 0) return 'USD/TRY kuru zorunlu.'
  if (sourceDebit.value > availableSource.value + 1e-10)
    return `${form.source_asset} bakiyesi yetersiz. Toplam gerekli ${formatSource(sourceDebit.value)}, kullanılabilir ${formatSource(availableSource.value)}.`
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
      transaction_type: 'BUY',
      source_asset: form.source_asset,
      target_asset: form.target_asset,
      source_quantity: sourceDebit.value,
      target_quantity: Number(form.target_quantity),
      price_currency: form.source_asset,
      source_unit_price: 1,
      target_unit_price: unitPriceUsd.value,
      usd_try: Number(form.usd_try),
      gross_usd: grossUsd.value,
      fee_usd: feeUsd.value,
      net_usd: grossUsd.value,
      platform: form.platform,
      note: form.note,
      transaction_at: new Date(form.transaction_at).toISOString(),
      metadata: {
        entry_flow: 'BUY_FROM_CASH',
        entered_unit_price: Number(form.unit_price),
        entered_price_currency: form.source_asset,
        trade_cost_source: tradeCostSource.value,
        fee_source: Number(form.fee_source || 0),
        source_balance_debit: sourceDebit.value,
        implied_target_unit_price_usd: unitPriceUsd.value,
      },
    })
    summaryOpen.value = false
    $q.notify({ type: 'positive', message: 'Alım kaydedildi.' })
    await router.push('/transactions')
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Alım kaydedilemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>
