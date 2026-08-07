<template>
  <q-page>
    <div class="page-wrap">
      <q-card flat class="section-card">
        <q-card-section>
          <div class="row items-center q-col-gutter-md">
            <div class="col">
              <div class="text-h6 text-weight-bold">Yatırım Bütçesi / Sermaye Hareketi</div>
              <div class="text-caption text-grey-7">
                Bankadan yatırım hesabına aktardığın bütçeyi veya yatırım hesabından dışarı çektiğin
                sermayeyi kaydet.
              </div>
            </div>
            <q-icon name="payments" color="primary" size="32px" />
          </div>
        </q-card-section>
        <q-separator />

        <q-card-section>
          <q-form class="row q-col-gutter-md" @submit.prevent="openSummary">
            <div class="col-12">
              <q-btn-toggle
                v-model="direction"
                spread
                no-caps
                unelevated
                toggle-color="primary"
                color="grey-2"
                text-color="grey-8"
                :options="[
                  { label: 'Yatırım Bütçesi Girişi', value: 'CASH_IN', icon: 'south_west' },
                  { label: 'Sermaye Çıkışı', value: 'CASH_OUT', icon: 'north_east' },
                ]"
              />
            </div>

            <div class="col-12 col-sm-6">
              <AppPopupSelect
                v-model="asset"
                :options="cashAssets"
                label="Para Birimi"
                :searchable="false"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="quantity"
                outlined
                type="number"
                min="0"
                step="any"
                label="Tutar"
              />
            </div>

            <div class="col-12">
              <TransactionBalanceContext
                :source-asset="direction === 'CASH_OUT' ? asset : null"
                :source-delta="direction === 'CASH_OUT' ? -Number(quantity || 0) : 0"
                :target-asset="direction === 'CASH_IN' ? asset : null"
                :target-delta="direction === 'CASH_IN' ? Number(quantity || 0) : 0"
                source-external-label="Banka / Dış Kaynak"
                target-external-label="Banka / Portföy Dışı"
              />
            </div>

            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="usdTry"
                outlined
                type="number"
                min="0"
                step="any"
                label="USD/TRY Kuru"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model="transactionAt"
                outlined
                type="datetime-local"
                label="İşlem Zamanı"
                stack-label
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input v-model.trim="platform" outlined label="Banka / Borsa Hesabı" />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="feeAmount"
                outlined
                type="number"
                min="0"
                step="any"
                :label="`Masraf (${asset})`"
              />
            </div>

            <div class="col-12">
              <q-banner rounded class="surface-soft">
                <div class="row q-col-gutter-md items-center">
                  <div class="col-6 col-md-3">
                    <div class="text-caption text-grey-6">Hareket Tutarı</div>
                    <div :class="direction === 'CASH_IN' ? 'amount-positive' : 'amount-negative'">
                      {{ formatAsset(quantity) }}
                    </div>
                  </div>
                  <div class="col-6 col-md-3">
                    <div class="text-caption text-grey-6">USD Normalize</div>
                    <div class="amount-strong">{{ formatUsd(grossUsd) }}</div>
                  </div>
                  <div class="col-6 col-md-3">
                    <div class="text-caption text-grey-6">Masraf</div>
                    <div class="amount-warning">{{ formatAsset(feeAmount) }}</div>
                  </div>
                  <div class="col-6 col-md-3">
                    <div class="text-caption text-grey-6">Raporlama</div>
                    <div class="text-weight-bold">
                      {{
                        direction === 'CASH_IN'
                          ? 'Yatırım bütçesine eklenir'
                          : 'Net sermayeden düşülür'
                      }}
                    </div>
                  </div>
                </div>
              </q-banner>
            </div>

            <div class="col-12">
              <q-input v-model.trim="note" outlined type="textarea" autogrow label="Not" />
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
            <div class="text-h6">Sermaye Hareketi Özeti</div>
            <div class="text-caption text-grey-7">
              Kaydetmeden önce seçili yatırım hesabındaki bakiye etkisini kontrol et.
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <TransactionBalanceContext
              compact
              :source-asset="direction === 'CASH_OUT' ? asset : null"
              :source-delta="direction === 'CASH_OUT' ? -Number(quantity || 0) : 0"
              :target-asset="direction === 'CASH_IN' ? asset : null"
              :target-delta="direction === 'CASH_IN' ? Number(quantity || 0) : 0"
              source-external-label="Banka / Dış Kaynak"
              target-external-label="Banka / Portföy Dışı"
            />
          </q-card-section>
          <q-list separator>
            <q-item
              ><q-item-section>Hareket</q-item-section
              ><q-item-section side>{{
                direction === 'CASH_IN' ? 'Yatırım Bütçesi Girişi' : 'Sermaye Çıkışı'
              }}</q-item-section></q-item
            >
            <q-item
              ><q-item-section>Tutar</q-item-section
              ><q-item-section
                side
                :class="direction === 'CASH_IN' ? 'amount-positive' : 'amount-negative'"
                >{{ formatAsset(quantity) }}</q-item-section
              ></q-item
            >
            <q-item
              ><q-item-section>Masraf</q-item-section
              ><q-item-section side>{{ formatAsset(feeAmount) }}</q-item-section></q-item
            >
            <q-item
              ><q-item-section>USD Karşılığı</q-item-section
              ><q-item-section side class="amount-strong">{{
                formatUsd(grossUsd)
              }}</q-item-section></q-item
            >
            <q-item
              ><q-item-section>USD/TRY</q-item-section
              ><q-item-section side>{{ Number(usdTry || 0).toFixed(4) }}</q-item-section></q-item
            >
            <q-item
              ><q-item-section>İşlem Zamanı</q-item-section
              ><q-item-section side>{{ formatDate(transactionAt) }}</q-item-section></q-item
            >
            <q-item
              ><q-item-section>Banka / Borsa</q-item-section
              ><q-item-section side>{{ platform || '—' }}</q-item-section></q-item
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
              label="Hareketi Onayla"
              no-caps
              @click="save"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </div>
  </q-page>
</template>

<script setup>
import { computed, ref } from 'vue'
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
const portfolio = usePortfolioStore()
const engine = useEngineStore()
const { formatDate, formatUsd } = useFormatters()
const cashAssets = ['USD', 'TRY']
const direction = ref('CASH_IN')
const asset = ref('TRY')
const quantity = ref(null)
const usdTry = ref(
  Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0) || null,
)
const transactionAt = ref(
  new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16),
)
const platform = ref('')
const feeAmount = ref(0)
const note = ref('')
const saving = ref(false)
const summaryOpen = ref(false)
const transactionRequestId = createTransactionRequestId()

const grossUsd = computed(() => assetToUsd(Number(quantity.value || 0)))
const feeUsd = computed(() => assetToUsd(Number(feeAmount.value || 0)))

function assetToUsd(value) {
  if (asset.value === 'USD') return Number(value || 0)
  const fx = Number(usdTry.value || 0)
  return fx > 0 ? Number(value || 0) / fx : 0
}

function formatAsset(value) {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: asset.value,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function validate() {
  if (!portfolio.selectedAccountId) return 'Aktif yatırım hesabı seçili değil.'
  if (!quantity.value || Number(quantity.value) <= 0) return 'Tutar sıfırdan büyük olmalı.'
  if (!usdTry.value || Number(usdTry.value) <= 0) return 'USD/TRY kuru zorunlu.'
  if (Number(feeAmount.value || 0) < 0) return 'Masraf negatif olamaz.'
  if (
    direction.value === 'CASH_OUT' &&
    Number(quantity.value) > Number(portfolio.quantities[asset.value] || 0) + 1e-10
  )
    return `${asset.value} bakiyesi sermaye çıkışı için yetersiz.`
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
    const incoming = direction.value === 'CASH_IN'
    await portfolio.addTransaction({
      id: transactionRequestId,
      transaction_type: direction.value,
      source_asset: incoming ? null : asset.value,
      target_asset: incoming ? asset.value : null,
      source_quantity: incoming ? null : Number(quantity.value),
      target_quantity: incoming ? Number(quantity.value) : null,
      price_currency: asset.value,
      source_unit_price: asset.value === 'USD' ? 1 : 1 / Number(usdTry.value),
      target_unit_price: asset.value === 'USD' ? 1 : 1 / Number(usdTry.value),
      usd_try: Number(usdTry.value),
      gross_usd: grossUsd.value,
      fee_usd: feeUsd.value,
      net_usd: grossUsd.value,
      platform: platform.value,
      note: note.value,
      transaction_at: new Date(transactionAt.value).toISOString(),
      metadata: {
        entry_flow: incoming ? 'INVESTMENT_BUDGET_TRANSFER' : 'CAPITAL_WITHDRAWAL',
        entered_fee_asset: asset.value,
        entered_fee_amount: Number(feeAmount.value || 0),
      },
    })
    summaryOpen.value = false
    $q.notify({
      type: 'positive',
      message: incoming ? 'Yatırım bütçesi girişi kaydedildi.' : 'Sermaye çıkışı kaydedildi.',
    })
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
