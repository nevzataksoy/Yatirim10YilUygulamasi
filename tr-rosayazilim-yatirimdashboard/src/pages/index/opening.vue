<template>
  <q-page>
    <div class="page-wrap">
      <div class="q-mb-lg">
        <div class="page-title">Başlangıç Portföyü</div>
        <div class="page-subtitle q-mt-xs">
          Uygulamayı kullanmaya başladığın tarihte sahip olduğun BTC, ETH, URA, nakit ve stablecoin
          bakiyelerini kaydet.
        </div>
      </div>
      <q-banner rounded class="surface-soft q-mb-lg">
        <template #avatar><q-icon name="info" color="primary" /></template>
        Her varlık için yalnız bir etkin <strong>OPENING</strong> zinciri bulunur. Eksik bir varlığı
        sonradan ekleyebilirsin; mevcut başlangıç miktarı veya maliyeti yanlışsa ikinci bir açılış
        eklemek yerine İşlemler ekranından mevcut kaydı <strong>revize et</strong>. Portföy
        sıfırlama yalnız bütün işlem geçmişini baştan girmek istediğinde kullanılmalıdır.
      </q-banner>
      <q-form @submit.prevent="save">
        <div class="row q-col-gutter-md">
          <div v-for="row in rows" :key="row.asset" class="col-12 col-lg-6">
            <q-card flat class="section-card full-height">
              <q-card-section>
                <div class="row items-center no-wrap q-mb-md">
                  <AssetAvatar :asset="row.asset" size="48px" />
                  <div class="q-ml-md">
                    <div class="text-h6 text-weight-bold">{{ row.asset }}</div>
                    <div class="text-caption text-grey-6">
                      {{
                        existingOpeningAssets.has(row.asset)
                          ? 'Başlangıç kaydı mevcut · düzeltme için revize et'
                          : 'Mevcut başlangıç bakiyesi'
                      }}
                    </div>
                  </div>
                  <q-space />
                  <q-chip
                    v-if="existingOpeningAssets.has(row.asset)"
                    dense
                    outline
                    color="positive"
                    icon="verified"
                  >
                    Kayıtlı
                  </q-chip>
                </div>
                <div class="row q-col-gutter-sm">
                  <div class="col-12 col-sm-6">
                    <q-input
                      v-model.number="row.quantity"
                      outlined
                      type="number"
                      step="any"
                      label="Miktar / Adet"
                      :disable="existingOpeningAssets.has(row.asset)"
                    />
                  </div>
                  <div class="col-12 col-sm-6">
                    <AppPopupSelect
                      v-model="row.price_currency"
                      :options="cashAssets"
                      label="Maliyet Para Birimi"
                      :searchable="false"
                      :disable="existingOpeningAssets.has(row.asset)"
                      @update:model-value="onPriceCurrencyChanged(row)"
                    />
                  </div>
                  <div class="col-12 col-sm-6">
                    <q-input
                      v-model.number="row.unit_price"
                      outlined
                      type="number"
                      step="any"
                      label="Ortalama Maliyet / Birim Değer"
                      :disable="existingOpeningAssets.has(row.asset)"
                    />
                  </div>
                  <div class="col-12 col-sm-6">
                    <q-input
                      v-model.number="row.usd_try"
                      outlined
                      type="number"
                      step="any"
                      label="USD/TRY"
                      :disable="existingOpeningAssets.has(row.asset)"
                    />
                  </div>
                  <div v-if="isStablecoin(row.price_currency)" class="col-12 col-sm-6">
                    <q-input
                      v-model.number="row.price_currency_stablecoin_usd"
                      outlined
                      type="number"
                      min="0"
                      step="any"
                      :label="`${row.price_currency}/USD İşlem Kuru`"
                      hint="Başlangıç tarihindeki stablecoin/USD değerini yaz."
                      :disable="existingOpeningAssets.has(row.asset)"
                    >
                      <template #append>
                        <q-btn
                          flat
                          dense
                          round
                          icon="auto_fix_high"
                          :disable="existingOpeningAssets.has(row.asset)"
                          @click="fillStablecoinRate(row)"
                        />
                      </template>
                    </q-input>
                  </div>
                  <div class="col-12">
                    <FinancialInstitutionSelect
                      v-model="row.platform"
                      label="Banka / Borsa / Aracı Kurum"
                      dialog-title="Başlangıç Bakiyesinin Kurumunu Seç"
                      :disabled="existingOpeningAssets.has(row.asset)"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
        <q-card flat class="section-card q-mt-lg">
          <q-card-section class="row q-col-gutter-md items-center">
            <div class="col-12 col-sm-6">
              <q-input
                v-model="openingDate"
                outlined
                type="date"
                label="Başlangıç Tarihi"
                stack-label
              />
            </div>
            <div class="col-12 col-sm-6 text-right">
              <q-btn
                push
                color="grey-3"
                text-color="grey-9"
                icon="close"
                label="Vazgeç"
                to="/portfolio"
                no-caps
              />
              <q-btn
                push
                color="primary"
                type="submit"
                icon="save"
                :loading="saving"
                label="Başlangıç Portföyünü Kaydet"
                no-caps
                class="q-ml-sm"
              />
            </div>
          </q-card-section>
        </q-card>
      </q-form>
    </div>
  </q-page>
</template>
<script setup>
import { computed, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import FinancialInstitutionSelect from '@/components/FinancialInstitutionSelect.vue'
import { ASSETS } from '@/services/portfolioAnalytics'
import { createTransactionRequestId } from '@/services/portfolioTransactions'
import {
  actualStablecoinUsdQuote,
  isStablecoin,
  SETTLEMENT_ASSET_OPTIONS,
  settlementAmountToUsd,
  stablecoinRatesMetadata,
} from '@/services/transactionCurrency'
import { useDisplayQuoteStore } from '@/stores/displayQuotes'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

const $q = useQuasar()
const router = useRouter()
const engine = useEngineStore()
const portfolio = usePortfolioStore()
const displayQuotes = useDisplayQuoteStore()
const cashAssets = SETTLEMENT_ASSET_OPTIONS
const saving = ref(false)
const openingDate = ref('2026-07-25')
const currentFx = Number(engine.market.find((item) => item.symbol === 'USD/TRY')?.value || 0)
const existingOpeningAssets = computed(
  () =>
    new Set(
      portfolio.selectedTransactions
        .filter((tx) => tx.transaction_type === 'OPENING')
        .map((tx) => tx.target_asset),
    ),
)

function currentStablecoinRate(asset) {
  return actualStablecoinUsdQuote(displayQuotes.quotes, asset) || null
}

const rows = reactive(
  ASSETS.map((asset) => ({
    request_id: createTransactionRequestId(),
    asset,
    quantity: null,
    price_currency: asset === 'TRY' ? 'TRY' : 'USD',
    unit_price:
      asset === 'USD' || asset === 'TRY'
        ? 1
        : isStablecoin(asset)
          ? currentStablecoinRate(asset)
          : null,
    price_currency_stablecoin_usd: null,
    usd_try: currentFx || null,
    platform: '',
  })),
)

function fillStablecoinRate(row) {
  row.price_currency_stablecoin_usd = currentStablecoinRate(row.price_currency)
}

function onPriceCurrencyChanged(row) {
  if (isStablecoin(row.price_currency)) fillStablecoinRate(row)
  else row.price_currency_stablecoin_usd = null
}

function grossUsd(row) {
  const quantity = Number(row.quantity || 0)
  const localCost = quantity * Number(row.unit_price || 0)
  return settlementAmountToUsd(localCost, row.price_currency, {
    usdTry: row.usd_try,
    stablecoinUsd: row.price_currency_stablecoin_usd,
  })
}

function validateRow(row) {
  if (Number(row.quantity || 0) <= 0) return ''
  if (Number(row.unit_price || 0) <= 0) return `${row.asset} birim maliyeti sıfırdan büyük olmalı.`
  if (Number(row.usd_try || 0) <= 0) return `${row.asset} için USD/TRY kuru zorunlu.`
  if (isStablecoin(row.price_currency) && Number(row.price_currency_stablecoin_usd || 0) <= 0) {
    return `${row.price_currency}/USD işlem kuru zorunlu.`
  }
  return ''
}

async function save() {
  const activeRows = rows.filter(
    (row) => !existingOpeningAssets.value.has(row.asset) && Number(row.quantity || 0) > 0,
  )
  if (!activeRows.length) {
    $q.notify({ type: 'warning', message: 'En az bir varlık miktarı gir.' })
    return
  }
  for (const row of activeRows) {
    const error = validateRow(row)
    if (error) {
      $q.notify({ type: 'warning', message: error })
      return
    }
  }
  saving.value = true
  try {
    await portfolio.addOpeningPositions(
      activeRows.map((row) => {
        const gross = grossUsd(row)
        const targetUsdRate = Number(row.quantity || 0) > 0 ? gross / Number(row.quantity) : 0
        return {
          id: row.request_id,
          target_asset: row.asset,
          target_quantity: Number(row.quantity),
          price_currency: row.price_currency,
          target_unit_price: Number(row.unit_price || 0),
          usd_try: Number(row.usd_try || 0) || null,
          gross_usd: gross,
          fee_usd: 0,
          net_usd: gross,
          platform: row.platform,
          note: 'Başlangıç portföyü',
          transaction_at: new Date(`${openingDate.value}T09:00:00`).toISOString(),
          metadata: {
            entry_flow: 'OPENING_BALANCE',
            ...stablecoinRatesMetadata([
              [row.price_currency, row.price_currency_stablecoin_usd],
              [row.asset, isStablecoin(row.asset) ? targetUsdRate : 0],
            ]),
          },
        }
      }),
    )
    $q.notify({ type: 'positive', message: 'Başlangıç portföyü kaydedildi.' })
    await router.push('/portfolio')
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