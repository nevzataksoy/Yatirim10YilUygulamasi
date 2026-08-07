<template>
  <q-page>
    <div class="page-wrap">
      <div class="q-mb-lg">
        <div class="page-title">Ayarlar</div>
        <div class="page-subtitle q-mt-xs">
          10 yıllık yatırım planı, hedef dağılım ve uygulama bağlantı ayarları.
        </div>
      </div>

      <div class="row q-col-gutter-lg">
        <div class="col-12 col-lg-7">
          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Yatırım Planı</div>
              <div class="text-caption text-grey-7">
                Bu değerler portföy hedefleri ve raporlama için kullanılacak.
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section>
              <q-form class="row q-col-gutter-md" @submit.prevent="savePlan">
                <div class="col-12 col-sm-6">
                  <q-input
                    v-model.number="plan.monthly_budget_usd"
                    outlined
                    type="number"
                    step="any"
                    label="Aylık Bütçe (USD)"
                  />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input
                    v-model="plan.start_date"
                    outlined
                    type="date"
                    label="Plan Başlangıcı"
                    stack-label
                  />
                </div>
                <div class="col-12 col-sm-4">
                  <q-input
                    v-model.number="plan.btc_target_pct"
                    outlined
                    type="number"
                    step="any"
                    label="BTC Hedef %"
                    suffix="%"
                  />
                </div>
                <div class="col-12 col-sm-4">
                  <q-input
                    v-model.number="plan.eth_target_pct"
                    outlined
                    type="number"
                    step="any"
                    label="ETH Hedef %"
                    suffix="%"
                  />
                </div>
                <div class="col-12 col-sm-4">
                  <q-input
                    v-model.number="plan.ura_target_pct"
                    outlined
                    type="number"
                    step="any"
                    label="URA Hedef %"
                    suffix="%"
                  />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input
                    v-model.number="plan.btc_eth_conversion_pct"
                    outlined
                    type="number"
                    step="any"
                    label="BTC/ETH Dönüşüm Oranı"
                    suffix="%"
                  />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input
                    v-model.number="plan.ura_usd_conversion_pct"
                    outlined
                    type="number"
                    step="any"
                    label="URA/USD Dönüşüm Oranı"
                    suffix="%"
                  />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input
                    v-model.number="plan.dca_day"
                    outlined
                    type="number"
                    min="1"
                    max="28"
                    label="Aylık Düzenli Alım Günü"
                  />
                </div>
                <div class="col-12 col-sm-6 flex items-center">
                  <q-toggle
                    v-model="plan.telegram_notifications"
                    color="primary"
                    label="Telegram bildirimleri açık"
                  />
                </div>
                <div class="col-12">
                  <q-banner
                    rounded
                    :class="
                      allocationTotal === 100
                        ? 'bg-green-1 text-green-10'
                        : 'bg-orange-1 text-orange-10'
                    "
                  >
                    Hedef dağılım toplamı: <strong>%{{ allocationTotal }}</strong>
                    <span v-if="allocationTotal !== 100">
                      — BTC + ETH + URA toplamını %100 yap.</span
                    >
                  </q-banner>
                </div>
                <div class="col-12 text-right">
                  <q-btn
                    push
                    color="primary"
                    type="submit"
                    :loading="saving"
                    icon="save"
                    label="Planı Kaydet"
                    no-caps
                  />
                </div>
              </q-form>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-lg-5">
          <q-card flat class="section-card q-mb-lg">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Supabase Bağlantısı</div>
              <div class="text-caption text-grey-7">
                Mobil istemcide yalnız Project URL ve publishable/anon key bulunur.
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section v-if="!connectionUnlocked">
              <q-banner rounded class="bg-blue-1 text-primary">
                <template #avatar><q-icon name="lock" /></template>
                Bağlantı bilgilerini görüntülemek veya değiştirmek için ayar şifresini doğrula.
                <template #action>
                  <q-btn
                    push
                    color="primary"
                    icon="lock_open"
                    label="Bağlantı Ayarını Aç"
                    no-caps
                    @click="requestConnectionSettings"
                  />
                </template>
              </q-banner>
              <div class="row items-center q-mt-md">
                <q-chip
                  dense
                  outline
                  :color="hasConnection ? 'positive' : 'warning'"
                  :icon="hasConnection ? 'cloud_done' : 'cloud_off'"
                >
                  {{ hasConnection ? `Yapılandırıldı · ${connectionSource}` : 'Yapılandırılmadı' }}
                </q-chip>
              </div>
            </q-card-section>
            <q-card-section v-else>
              <q-input v-model.trim="connection.url" outlined label="Project URL" />
              <q-input
                v-model.trim="connection.publishableKey"
                outlined
                label="Publishable Key"
                class="q-mt-md"
              />
              <q-banner
                v-if="auth.connectionHealth.checkedAt"
                rounded
                :class="connectionHealthClass"
                class="q-mt-md"
              >
                <template #avatar>
                  <q-icon
                    :name="auth.connectionHealth.status === 'ok' ? 'verified_user' : 'gpp_bad'"
                  />
                </template>
                {{ auth.connectionHealth.message }}
                <div class="text-caption q-mt-xs">
                  Auth: {{ auth.connectionHealth.authApi }} · RLS:
                  {{ auth.connectionHealth.authenticatedRls }}
                  <span v-if="auth.connectionHealth.latencyMs">
                    · {{ auth.connectionHealth.latencyMs }} ms</span
                  >
                </div>
              </q-banner>
              <div class="row items-center q-mt-md">
                <q-chip
                  dense
                  outline
                  :color="hasConnection ? 'positive' : 'warning'"
                  :icon="hasConnection ? 'cloud_done' : 'cloud_off'"
                >
                  {{ hasConnection ? `Bağlı · ${connection.source}` : 'Yapılandırılmadı' }}
                </q-chip>
                <q-space />
                <q-btn
                  flat
                  color="grey-8"
                  icon="password"
                  label="Ayar Şifresini Değiştir"
                  no-caps
                  class="q-mr-sm"
                  @click="requestPasswordChange"
                />
                <q-btn
                  flat
                  color="grey-8"
                  icon="lock"
                  label="Kilitle"
                  no-caps
                  class="q-mr-sm"
                  @click="lockConnectionSettings"
                />
                <q-btn
                  outline
                  color="primary"
                  icon="network_check"
                  label="Bağlantıyı Test Et"
                  no-caps
                  class="q-mr-sm"
                  :loading="testingConnection"
                  @click="testConnection"
                />
                <q-btn
                  push
                  color="primary"
                  icon="save"
                  label="Test Et ve Kaydet"
                  no-caps
                  :loading="savingConnection"
                  @click="saveConnection"
                />
              </div>
            </q-card-section>
          </q-card>

          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Model Eşikleri</div>
              <div class="text-caption text-grey-7">
                Gölge doğrulama sırasında otomatik değiştirilmez.
              </div>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item v-for="item in thresholds" :key="item.code">
                <q-item-section>
                  <q-item-label class="row items-center q-gutter-xs">
                    <span>{{ item.label }}</span>
                    <q-badge outline color="primary">{{ item.code }}</q-badge>
                  </q-item-label>
                </q-item-section>
                <q-item-section side
                  ><strong>{{ item.value }}</strong></q-item-section
                >
              </q-item>
            </q-list>
          </q-card>
        </div>
      </div>

      <q-card flat class="section-card danger-zone q-mt-lg">
        <q-card-section class="row items-center q-col-gutter-md">
          <div class="col-12 col-md">
            <div class="text-h6 text-weight-bold text-negative">Tehlikeli Bölge</div>
            <div class="text-body2 text-grey-8 q-mt-xs">
              <strong>{{ portfolio.selectedAccount?.name || 'Seçili portföy' }}</strong>
              hesabının tüm işlem ve revizyon geçmişini kalıcı olarak sıfırlar. Piyasa verileri,
              Python sinyalleri, Telegram bildirim geçmişi ve yatırım ayarları korunur.
            </div>
          </div>
          <div class="col-12 col-md-auto">
            <q-btn
              push
              color="negative"
              icon="delete_sweep"
              label="İşlem Geçmişini Sıfırla"
              no-caps
              :disable="!portfolio.selectedAccount"
              @click="openResetDialog"
            />
          </div>
        </q-card-section>
      </q-card>
    </div>

    <SettingsPasswordDialog
      v-model="settingsPasswordDialog"
      :force-setup="passwordDialogPurpose === 'change'"
      @verified="handleSettingsPasswordVerified"
    />

    <q-dialog v-model="resetDialog" persistent>
      <q-card class="reset-dialog-card">
        <q-card-section class="row items-start no-wrap q-gutter-md">
          <q-avatar color="negative" text-color="white" icon="warning" />
          <div>
            <div class="text-h6 text-weight-bold">Portföy geçmişini sıfırla</div>
            <div class="text-body2 text-grey-7 q-mt-xs">
              Bu işlem geri alınamaz. Açılış bakiyeleri, alımlar, satışlar, dönüşümler, sermaye
              hareketleri, revizyonlar ve iptal kayıtları silinir.
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-banner rounded class="bg-red-1 text-negative q-mb-md">
            Yalnız <strong>{{ portfolio.selectedAccount?.name }}</strong> hesabının işlem geçmişi
            silinecek. Kullanıcı profili ve yatırım planı değişmeyecek.
          </q-banner>
          <q-checkbox
            v-model="resetAcknowledged"
            color="negative"
            label="Bu işlemin kalıcı olduğunu ve geri alınamayacağını anlıyorum."
          />
          <q-input
            v-model="resetConfirmation"
            outlined
            class="q-mt-md"
            label="Onay ifadesi"
            hint="Devam etmek için PORTFÖYÜ SIFIRLA yaz."
            autocomplete="off"
          />
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="popup-actions">
          <q-btn
            push
            color="grey-7"
            label="Vazgeç"
            no-caps
            :disable="resetting"
            @click="closeResetDialog"
          />
          <q-btn
            push
            color="negative"
            icon="delete_forever"
            label="Kalıcı Olarak Sıfırla"
            no-caps
            :loading="resetting"
            :disable="!canResetPortfolio"
            @click="resetPortfolioHistory"
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
import SettingsPasswordDialog from '@/components/SettingsPasswordDialog.vue'
import { THRESHOLD_LABELS } from '@/services/presentation'
import { useAuthStore } from '@/stores/auth'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'
import { getStoredConnection, hasSupabaseConfig } from '@/services/supabase'

const $q = useQuasar()
const router = useRouter()
const auth = useAuthStore()
const engine = useEngineStore()
const portfolio = usePortfolioStore()
const saving = ref(false)
const resetDialog = ref(false)
const resetAcknowledged = ref(false)
const resetConfirmation = ref('')
const resetting = ref(false)
const settingsPasswordDialog = ref(false)
const passwordDialogPurpose = ref('access')
const connectionUnlocked = ref(false)
const connectionRevision = ref(0)
const testingConnection = ref(false)
const savingConnection = ref(false)
const connection = reactive({
  url: '',
  publishableKey: '',
  source: 'none',
})

const defaults = {
  monthly_budget_usd: 200,
  start_date: '2026-07-25',
  btc_target_pct: 37.5,
  eth_target_pct: 37.5,
  ura_target_pct: 25,
  btc_eth_conversion_pct: 50,
  ura_usd_conversion_pct: 50,
  dca_day: 25,
  telegram_notifications: true,
}
const plan = reactive({ ...defaults, ...(portfolio.settings || {}) })

const allocationTotal = computed(
  () =>
    Number(plan.btc_target_pct || 0) +
    Number(plan.eth_target_pct || 0) +
    Number(plan.ura_target_pct || 0),
)
const hasConnection = computed(() => {
  connectionRevision.value
  return hasSupabaseConfig()
})
const connectionSource = computed(() => {
  connectionRevision.value
  return getStoredConnection().source
})
const connectionHealthClass = computed(() =>
  auth.connectionHealth.status === 'ok' ? 'bg-green-1 text-green-10' : 'bg-red-1 text-negative',
)
const canResetPortfolio = computed(
  () =>
    resetAcknowledged.value &&
    resetConfirmation.value.trim().toLocaleUpperCase('tr-TR') === 'PORTFÖYÜ SIFIRLA' &&
    !resetting.value,
)

const thresholds = [
  { code: 'MIN_DATA_QUALITY', label: THRESHOLD_LABELS.MIN_DATA_QUALITY, value: 80 },
  { code: 'MIN_EDGE', label: THRESHOLD_LABELS.MIN_EDGE, value: 70 },
  { code: 'MIN_CONFIDENCE', label: THRESHOLD_LABELS.MIN_CONFIDENCE, value: 70 },
  { code: 'STRONG_EDGE', label: THRESHOLD_LABELS.STRONG_EDGE, value: 80 },
  { code: 'STRONG_CONFIDENCE', label: THRESHOLD_LABELS.STRONG_CONFIDENCE, value: 80 },
]

async function savePlan() {
  if (Math.abs(allocationTotal.value - 100) > 0.001) {
    $q.notify({ type: 'warning', message: 'BTC + ETH + URA hedef dağılımı %100 olmalı.' })
    return
  }
  if (Number(plan.dca_day) < 1 || Number(plan.dca_day) > 28) {
    $q.notify({ type: 'warning', message: 'Düzenli alım günü 1 ile 28 arasında olmalı.' })
    return
  }

  saving.value = true
  try {
    await portfolio.saveSettings({ ...plan })
    $q.notify({ type: 'positive', message: 'Yatırım planı kaydedildi.' })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Ayarlar kaydedilemedi.',
    })
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testingConnection.value = true
  try {
    await auth.runConnectionTest(connection, { includeSession: true })
    $q.notify({ type: 'positive', message: auth.connectionHealth.message })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Bağlantı testi başarısız.',
    })
  } finally {
    testingConnection.value = false
  }
}

async function saveConnection() {
  savingConnection.value = true
  try {
    const result = await auth.configureConnection(connection)
    connectionRevision.value += 1
    lockConnectionSettings()

    if (result.changed) {
      portfolio.reset()
      engine.reset()
      $q.notify({
        type: 'positive',
        message: 'Bağlantı değiştirildi. Yeni Supabase projesinde yeniden giriş yap.',
      })
      await router.replace('/login')
      return
    }

    $q.notify({ type: 'positive', message: 'Bağlantı ve Auth/RLS erişimi doğrulandı.' })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Bağlantı kaydedilemedi.',
    })
  } finally {
    savingConnection.value = false
  }
}

function requestConnectionSettings() {
  passwordDialogPurpose.value = 'access'
  settingsPasswordDialog.value = true
}

function requestPasswordChange() {
  passwordDialogPurpose.value = 'change'
  settingsPasswordDialog.value = true
}

function handleSettingsPasswordVerified({ created }) {
  if (passwordDialogPurpose.value === 'change') {
    $q.notify({ type: 'positive', message: 'Ayar şifresi değiştirildi.' })
    passwordDialogPurpose.value = 'access'
    return
  }

  Object.assign(connection, getStoredConnection())
  connectionUnlocked.value = true
  if (created) $q.notify({ type: 'positive', message: 'Ayar şifresi oluşturuldu.' })
}

function lockConnectionSettings() {
  connectionUnlocked.value = false
  Object.assign(connection, { url: '', publishableKey: '', source: 'none' })
}

function openResetDialog() {
  resetAcknowledged.value = false
  resetConfirmation.value = ''
  resetDialog.value = true
}

function closeResetDialog() {
  if (resetting.value) return
  resetDialog.value = false
  resetAcknowledged.value = false
  resetConfirmation.value = ''
}

async function resetPortfolioHistory() {
  if (!canResetPortfolio.value) return

  resetting.value = true
  try {
    const deletedCount = await portfolio.resetSelectedAccountTransactionHistory('PORTFÖYÜ SIFIRLA')
    resetDialog.value = false
    resetAcknowledged.value = false
    resetConfirmation.value = ''
    $q.notify({
      type: 'positive',
      message: `${deletedCount} işlem kaydı silindi. Portföy sıfır bakiyeyle kullanıma hazır.`,
    })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Portföy geçmişi sıfırlanamadı.',
    })
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.danger-zone {
  border-color: rgba(193, 0, 21, 0.3);
}

.reset-dialog-card {
  width: min(560px, calc(100vw - 32px));
  max-width: 560px;
}
</style>
