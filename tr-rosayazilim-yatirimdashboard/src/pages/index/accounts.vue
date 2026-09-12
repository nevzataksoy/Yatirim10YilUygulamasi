<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-end justify-between q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="page-title">Portföy Hesaplarım</div>
          <div class="page-subtitle q-mt-xs">
            Tek kullanıcı hesabın altında kendin, eşin veya çocuğun için ayrı portföyler yönet.
            Seçtiğin portföy uygulamanın aktif çalışma alanı olur.
          </div>
        </div>
        <div class="col-auto">
          <q-btn
            push
            color="primary"
            icon="add"
            label="Yeni Portföy Hesabı"
            no-caps
            @click="openCreateDialog"
          />
        </div>
      </div>

      <q-banner rounded class="surface-soft q-mb-lg">
        <template #avatar><q-icon name="info" color="primary" /></template>
        Dashboard, Portföy, İşlemler, Raporlar ve veri girişleri aktif portföye göre çalışır.
        Sinyaller ise portföyden bağımsız BTC/ETH ve URA/USD kararlarıdır.
      </q-banner>

      <div class="row q-col-gutter-md">
        <div
          v-for="account in portfolio.activeAccounts"
          :key="account.id"
          class="col-12 col-md-6 col-xl-4"
        >
          <q-card
            flat
            class="section-card full-height portfolio-account-card"
            :class="{
              'portfolio-account-card--selected': account.id === portfolio.selectedAccountId,
            }"
          >
            <q-card-section>
              <div class="row items-start no-wrap">
                <q-avatar
                  size="48px"
                  :color="account.id === portfolio.selectedAccountId ? 'primary' : 'teal-1'"
                  :text-color="account.id === portfolio.selectedAccountId ? 'white' : 'primary'"
                  icon="account_balance_wallet"
                />
                <div class="col q-ml-md min-width-0">
                  <div class="row items-center q-gutter-xs">
                    <div class="text-h6 text-weight-bold ellipsis">{{ account.name }}</div>
                    <q-badge v-if="account.is_default" outline color="primary">Varsayılan</q-badge>
                  </div>
                  <div class="text-caption text-grey-7 q-mt-xs">
                    {{ account.base_currency || 'USD' }} baz para birimi ·
                    {{ transactionCount(account.id) }} audit kaydı
                  </div>
                </div>
              </div>
            </q-card-section>
            <q-separator />
            <q-card-actions class="q-pa-md">
              <q-chip
                v-if="account.id === portfolio.selectedAccountId"
                color="green-1"
                text-color="positive"
                icon="check_circle"
              >
                Aktif Çalışma Alanı
              </q-chip>
              <q-space />
              <q-btn
                v-if="account.id !== portfolio.selectedAccountId"
                push
                color="primary"
                icon="login"
                label="Bu Portföyde Çalış"
                no-caps
                @click="activateAccount(account)"
              />
              <q-btn
                v-else
                flat
                color="primary"
                icon="open_in_new"
                label="Portföyü Aç"
                no-caps
                to="/portfolio"
              />
            </q-card-actions>
          </q-card>
        </div>
      </div>

      <q-card v-if="!portfolio.activeAccounts.length" flat class="section-card">
        <q-card-section class="text-center q-pa-xl">
          <q-icon name="account_balance_wallet" size="54px" color="grey-4" />
          <div class="text-h6 q-mt-md">Portföy hesabı bulunmuyor</div>
          <div class="text-grey-6 q-mt-xs">İlk çalışma alanını oluşturarak başlayabilirsin.</div>
          <q-btn
            push
            color="primary"
            icon="add"
            label="Portföy Hesabı Oluştur"
            no-caps
            class="q-mt-lg"
            @click="openCreateDialog"
          />
        </q-card-section>
      </q-card>
    </div>

    <q-dialog v-model="createDialog" persistent>
      <q-card class="portfolio-account-dialog">
        <q-card-section>
          <div class="text-h6 text-weight-bold">Yeni Portföy Hesabı</div>
          <div class="text-body2 text-grey-7 q-mt-xs">
            Bu hesap aynı varlıkları ve ortak yatırım planını kullanır; işlem defteri tamamen ayrı
            tutulur.
          </div>
        </q-card-section>
        <q-separator />
        <q-form @submit.prevent="createAccount">
          <q-card-section>
            <q-input
              ref="nameInput"
              v-model.trim="form.name"
              outlined
              label="Portföy Hesabı Adı"
              placeholder="Örn. Eşim İçin Portföy"
              maxlength="80"
              counter
              autofocus
              :rules="[
                (value) => String(value || '').trim().length >= 2 || 'En az 2 karakter yazmalısın.',
              ]"
            >
              <template #prepend><q-icon name="badge" /></template>
            </q-input>
            <AppPopupSelect
              v-model="form.baseCurrency"
              :options="currencyOptions"
              label="Baz Para Birimi"
              dialog-title="Baz Para Birimini Seç"
              dialog-caption="Muhasebe defteri USD normalize çalışmaya devam eder; bu alan hesabın tercihidir."
              :searchable="false"
              :clearable="false"
              class="q-mt-md"
            >
              <template #prepend><q-icon name="currency_exchange" /></template>
            </AppPopupSelect>
          </q-card-section>
          <q-separator />
          <q-card-actions class="popup-action-footer q-pa-md">
            <q-space />
            <q-btn
              push
              color="grey-3"
              text-color="grey-9"
              icon="close"
              label="Vazgeç"
              no-caps
              :disable="creating"
              @click="closeCreateDialog"
            />
            <q-btn
              push
              color="primary"
              icon="add"
              label="Oluştur ve Seç"
              type="submit"
              no-caps
              :loading="creating"
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { nextTick, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import { usePortfolioStore } from '@/stores/portfolio'

const $q = useQuasar()
const router = useRouter()
const portfolio = usePortfolioStore()
const createDialog = ref(false)
const creating = ref(false)
const nameInput = ref(null)
const form = reactive({ name: '', baseCurrency: 'USD' })

const currencyOptions = [
  { label: 'Amerikan Doları (USD)', value: 'USD', caption: 'USD baz para birimi' },
  { label: 'Türk Lirası (TRY)', value: 'TRY', caption: 'TRY baz para birimi' },
]

function transactionCount(accountId) {
  return portfolio.transactions.filter((transaction) => transaction.account_id === accountId).length
}

function openCreateDialog() {
  form.name = ''
  form.baseCurrency = 'USD'
  createDialog.value = true
  nextTick(() => nameInput.value?.focus?.())
}

function closeCreateDialog() {
  if (!creating.value) createDialog.value = false
}

function activateAccount(account) {
  portfolio.selectAccount(account.id)
  $q.notify({ type: 'positive', message: `${account.name} aktif çalışma alanı oldu.` })
}

async function createAccount() {
  creating.value = true
  try {
    const account = await portfolio.createAccount({
      name: form.name,
      baseCurrency: form.baseCurrency,
    })
    createDialog.value = false
    $q.notify({ type: 'positive', message: `${account.name} oluşturuldu ve seçildi.` })
    await router.push('/portfolio')
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Portföy hesabı oluşturulamadı.',
    })
  } finally {
    creating.value = false
  }
}
</script>
