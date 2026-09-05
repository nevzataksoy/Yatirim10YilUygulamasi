<template>
  <q-page>
    <div class="page-wrap">
      <div class="q-mb-lg">
        <div class="page-title">Sermaye Hareketi</div>
        <div class="page-subtitle q-mt-xs">
          Portföye dışarıdan nakit ekle veya dışarı nakit çıkar.
        </div>
      </div>
      <q-form @submit.prevent="openSummary">
        <q-card flat class="section-card">
          <q-card-section class="row q-col-gutter-md">
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.kind"
                :options="kindOptions"
                label="Hareket Türü"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="form.asset"
                :options="cashAssets"
                label="Para Birimi"
                :searchable="false"
              />
            </div>
            <div class="col-12">
              <TransactionBalanceContext
                :source-asset="form.kind === 'CASH_OUT' ? form.asset : ''"
                :source-delta="form.kind === 'CASH_OUT' ? -Number(form.quantity || 0) : 0"
                :target-asset="form.kind === 'CASH_IN' ? form.asset : ''"
                :target-delta="form.kind === 'CASH_IN' ? Number(form.quantity || 0) : 0"
              />
            </div>
            <div v-if="form.kind === 'CASH_OUT'" class="col-12">
              <div class="text-caption text-grey-7 q-mb-xs">Sermaye Çıkışı Kısayolu</div>
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
                v-model.number="form.quantity"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Miktar (${form.asset})`"
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
                label="Tarih / Saat"
                stack-label
              />
            </div>
            <div class="col-12 col-sm-6">
              <FinancialInstitutionSelect
                v-model="form.platform"
                label="Banka / Borsa / Aracı Kurum"
                dialog-title="Sermaye Hareketi Kurumunu Seç"
              />
            </div>
            <div class="col-12">
              <q-banner rounded class="surface-soft">
                <div class="row q-col-gutter-md">
                  <div class="col-6 col-sm-3">
                    <div class="text-caption text-grey-6">Hareket</div>
                    <div class="text-weight-bold">
                      {{ form.kind === 'CASH_IN' ? 'Giriş' : 'Çıkış' }}
                    </div>
                  </div>
                  <div class="col-6 col-sm-3">
                    <div class="text-caption text-grey-6">Tutar</div>
                    <div class="amount-primary">{{ formatCash(form.quantity) }}</div>
                  </div>
                  <div class="col-6 col-sm-3">
                    <div class="text-caption text-grey-6">USD Karşılığı</div>
                    <div class="amount-strong">{{ formatUsd(grossUsd) }}</div>
                  </div>
                  <div class="col-6 col-sm-3">
                    <div class="text-caption text-grey-6">İşlem Sonrası</div>
                    <div :class="remaining < -1e-10 ? 'amount-negative' : 'amount-positive'">
                      {{ formatCash(remaining) }}
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
          </q-card-section>
        </q-card>
      </q-form>
    </div>
    <q-dialog v-model="summaryOpen">
      <q-card style="width: min(94vw, 680px)">
        <q-card-section>
          <div class="text-h6">Sermaye Hareketi Özeti</div>
          <div class="text-caption text-grey-7">
            Kaydetmeden önce hareketin seçili portföy hesabına etkisini kontrol et.
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <TransactionBalanceContext
            compact
            :source-asset="form.kind === 'CASH_OUT' ? form.asset : ''"
            :source-delta="form.kind === 'CASH_OUT' ? -Number(form.quantity || 0) : 0"
            :target-asset="form.kind === 'CASH_IN' ? form.asset : ''"
            :target-delta="form.kind === 'CASH_IN' ? Number(form.quantity || 0) : 0"
          />
        </q-card-section>
        <q-list separator>
          <q-item>
            <q-item-section>Hareket</q-item-section>
            <q-item-section side>{{
              form.kind === 'CASH_IN' ? 'Sermaye Girişi' : 'Sermaye Çıkışı'
            }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Miktar</q-item-section>
            <q-item-section
              side
              :class="form.kind === 'CASH_IN' ? 'amount-positive' : 'amount-negative'"
            >
              {{ formatCash(form.quantity) }}
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>USD Karşılığı</q-item-section>
            <q-item-section side class="amount-strong">{{ formatUsd(grossUsd) }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Kur</q-item-section>
            <q-item-section side>{{ Number(form.usd_try || 0).toFixed(4) }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Kurum</q-item-section>
            <q-item-section side>{{ form.platform || '—' }}</q-item-section>
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
            label="Sermaye Hareketini Onayla"
            no-caps
            @click="save"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
<script setup>
import { computed, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import FinancialInstitutionSelect from '@/components/FinancialInstitutionSelect.vue'
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
const saving = ref(false)
const summaryOpen = ref(false)
const transactionRequestId = createTransactionRequestId()
const cashAssets = ['TRY', 'USD']
const kindOptions = [
  { label: 'Sermaye Girişi', value: 'CASH_IN', icon: 'south_west' },
  { label: 'Sermaye Çıkışı', value: 'CASH_OUT', icon: 'north_east' },
]
const marketUsdTry = Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0)
const form = reactive({
  kind: 'CASH_IN',
  asset: 'TRY',
  quantity: null,
  usd_try: marketUsdTry || null,
  transaction_at: new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16),
  platform: '',
  note: '',
})
const availableCash = computed(() => Number(portfolio.quantities[form.asset] || 0))
const grossUsd = computed(() => {
  const amount = Number(form.quantity || 0)
  if (form.asset === 'USD') return amount
  const fx = Number(form.usd_try || 0)
  return fx > 0 ? amount / fx : 0
})
const remaining = computed(
  () =>
    availableCash.value +
    (form.kind === 'CASH_IN' ? Number(form.quantity || 0) : -Number(form.quantity || 0)),
)
function formatCash(value) {
  return `${formatNumber(value, 2)} ${form.asset}`
}
function usePercentage(pct) {
  form.quantity = Number(((availableCash.value * pct) / 100).toPrecision(12))
}
function validate() {
  if (!portfolio.selectedAccountId) return 'Aktif yatırım hesabı seçili değil.'
  if (Number(form.quantity || 0) <= 0) return 'Miktar sıfırdan büyük olmalı.'
  if (Number(form.usd_try || 0) <= 0) return 'USD/TRY kuru zorunlu.'
  if (form.kind === 'CASH_OUT' && Number(form.quantity) > availableCash.value + 1e-10) {
    return `${form.asset} bakiyesi yetersiz.`
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
    const isIn = form.kind === 'CASH_IN'
    await portfolio.addTransaction({
      id: transactionRequestId,
      transaction_type: form.kind,
      source_asset: isIn ? null : form.asset,
      target_asset: isIn ? form.asset : null,
      source_quantity: isIn ? null : Number(form.quantity),
      target_quantity: isIn ? Number(form.quantity) : null,
      price_currency: form.asset,
      source_unit_price: isIn ? null : form.asset === 'USD' ? 1 : 1 / Number(form.usd_try),
      target_unit_price: isIn ? (form.asset === 'USD' ? 1 : 1 / Number(form.usd_try)) : null,
      usd_try: Number(form.usd_try),
      gross_usd: grossUsd.value,
      fee_usd: 0,
      net_usd: isIn ? grossUsd.value : -grossUsd.value,
      platform: form.platform,
      note: form.note,
      transaction_at: new Date(form.transaction_at).toISOString(),
      metadata: { entry_flow: form.kind },
    })
    summaryOpen.value = false
    $q.notify({ type: 'positive', message: 'Sermaye hareketi kaydedildi.' })
    await router.push('/transactions')
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Kayıt başarısız.',
    })
  } finally {
    saving.value = false
  }
}
</script>
