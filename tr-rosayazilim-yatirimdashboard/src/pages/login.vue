<template>
  <q-layout view="hHh lpR fFf" class="login-layout">
    <q-page-container>
      <q-page class="login-page flex flex-center q-pa-md">
        <q-card class="login-card" flat>
          <q-card-section class="q-pa-lg q-pb-sm">
            <AppLogo />
            <div class="text-h4 text-weight-bold q-mt-xl">Portföyünü tek yerden yönet</div>
            <div class="text-body2 text-grey-7 q-mt-sm">
              BTC, ETH ve URA yatırımlarını takip et; Investment Engine kararlarını portföyünle
              birlikte değerlendir.
            </div>
          </q-card-section>

          <q-card-section class="q-pa-lg q-pt-md">
            <q-tabs
              v-model="mode"
              dense
              no-caps
              active-color="primary"
              indicator-color="primary"
              class="q-mb-lg"
            >
              <q-tab name="login" label="Giriş" />
              <q-tab name="register" label="Kayıt" />
            </q-tabs>

            <q-form @submit.prevent="submit">
              <div v-if="mode === 'register'" class="row q-col-gutter-sm">
                <div class="col-6"><q-input v-model.trim="firstName" outlined label="Ad" /></div>
                <div class="col-6"><q-input v-model.trim="lastName" outlined label="Soyad" /></div>
              </div>

              <q-input
                v-model.trim="email"
                outlined
                type="email"
                label="E-posta"
                autocomplete="email"
                class="q-mt-md"
                :rules="[(value) => Boolean(value) || 'E-posta gerekli']"
              >
                <template #prepend><q-icon name="mail" /></template>
              </q-input>

              <q-input
                v-model="password"
                outlined
                :type="showPassword ? 'text' : 'password'"
                label="Şifre"
                autocomplete="current-password"
                class="q-mt-sm"
                :rules="[(value) => value.length >= 6 || 'En az 6 karakter']"
              >
                <template #prepend><q-icon name="lock" /></template>
                <template #append>
                  <q-icon
                    :name="showPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showPassword = !showPassword"
                  />
                </template>
              </q-input>

              <q-btn
                push
                color="primary"
                size="lg"
                class="full-width q-mt-md"
                :label="mode === 'login' ? 'Giriş yap' : 'Hesap oluştur'"
                :loading="auth.loading"
                type="submit"
                no-caps
              />
              <q-btn
                v-if="mode === 'login'"
                flat
                color="primary"
                class="full-width q-mt-sm"
                label="Şifremi unuttum"
                no-caps
                @click="openPasswordReset"
              />
            </q-form>

            <div class="row items-center q-my-lg">
              <q-separator class="col" />
              <div class="text-caption text-grey-6 q-px-md">veya</div>
              <q-separator class="col" />
            </div>

            <q-btn
              outline
              color="primary"
              icon="science"
              class="full-width"
              label="Demo ile aç"
              no-caps
              @click="demoLogin"
            />

            <q-btn
              v-if="hasConnection"
              flat
              color="grey-8"
              icon="settings_ethernet"
              class="full-width q-mt-sm"
              label="Bağlantı ayarı"
              no-caps
              @click="requestConnectionSettings"
            />

            <q-banner v-if="!hasConnection" rounded class="bg-amber-1 text-amber-10 q-mt-lg">
              <template #avatar><q-icon name="cloud_off" /></template>
              Supabase yapılandırılmadı. Arayüzü ve veri girişlerini Demo modu ile test edebilirsin.
              <template #action>
                <q-btn
                  flat
                  color="primary"
                  label="Bağlantı ayarı"
                  no-caps
                  @click="requestConnectionSettings"
                />
              </template>
            </q-banner>
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>

    <SettingsPasswordDialog v-model="settingsPasswordDialog" @verified="openConnectionSettings" />

    <q-dialog v-model="showConnection" @hide="clearConnectionDraft">
      <q-card style="width: min(92vw, 560px)">
        <q-card-section>
          <div class="text-h6">Supabase bağlantısı</div>
          <div class="text-caption text-grey-7">
            Publishable/anon key kullan. service_role anahtarı istemciye yazılmaz.
          </div>
        </q-card-section>
        <q-card-section>
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
              <q-icon :name="auth.connectionHealth.status === 'ok' ? 'cloud_done' : 'cloud_off'" />
            </template>
            {{ auth.connectionHealth.message }}
            <div v-if="auth.connectionHealth.latencyMs" class="text-caption q-mt-xs">
              {{ auth.connectionHealth.latencyMs }} ms
            </div>
          </q-banner>
        </q-card-section>
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
            outline
            color="primary"
            icon="network_check"
            label="Test Et"
            no-caps
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
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="passwordResetDialog">
      <q-card style="width: min(92vw, 460px)">
        <q-card-section>
          <div class="text-h6">Şifremi unuttum</div>
          <div class="text-body2 text-grey-7 q-mt-xs">
            E-posta adresine tek kullanımlık şifre yenileme bağlantısı gönderilecek.
          </div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.trim="resetEmail"
            outlined
            type="email"
            label="E-posta"
            autocomplete="email"
          />
        </q-card-section>
        <q-card-actions align="right" class="popup-action-footer q-pa-md">
          <q-btn flat color="grey-8" label="Vazgeç" no-caps v-close-popup />
          <q-btn
            push
            color="primary"
            icon="forward_to_inbox"
            label="Bağlantıyı Gönder"
            no-caps
            :loading="auth.loading"
            @click="sendPasswordReset"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import AppLogo from '@/components/AppLogo.vue'
import SettingsPasswordDialog from '@/components/SettingsPasswordDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'
import { getStoredConnection, hasSupabaseConfig } from '@/services/supabase'

const $q = useQuasar()
const router = useRouter()
const auth = useAuthStore()
const portfolio = usePortfolioStore()
const engine = useEngineStore()

const mode = ref('login')
const email = ref('')
const password = ref('')
const firstName = ref('')
const lastName = ref('')
const showPassword = ref(false)
const settingsPasswordDialog = ref(false)
const showConnection = ref(false)
const connection = reactive({ url: '', publishableKey: '', source: 'none' })
const connectionRevision = ref(0)
const testingConnection = ref(false)
const savingConnection = ref(false)
const passwordResetDialog = ref(false)
const resetEmail = ref('')
const hasConnection = computed(() => {
  connectionRevision.value
  return hasSupabaseConfig()
})
const connectionHealthClass = computed(() =>
  auth.connectionHealth.status === 'ok' ? 'bg-green-1 text-green-10' : 'bg-red-1 text-negative',
)

async function submit() {
  try {
    if (mode.value === 'register') {
      await auth.signUp(email.value, password.value, firstName.value, lastName.value)
      $q.notify({
        type: 'positive',
        message: 'Hesap oluşturuldu. E-posta doğrulaması gerekiyorsa gelen kutunu kontrol et.',
      })
      if (!auth.authenticated) mode.value = 'login'
    } else {
      await auth.signIn(email.value, password.value)
    }

    if (auth.authenticated) {
      await Promise.allSettled([portfolio.sync(), engine.sync()])
      await router.replace('/')
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'İşlem başarısız.',
    })
  }
}

async function demoLogin() {
  auth.demoLogin()
  portfolio.loadDemo()
  engine.loadDemo()
  await router.replace('/')
}

async function testConnection() {
  testingConnection.value = true
  try {
    await auth.runConnectionTest(connection, { includeSession: false })
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
    await auth.configureConnection(connection)
    connectionRevision.value += 1
    showConnection.value = false
    $q.notify({ type: 'positive', message: 'Supabase bağlantısı test edildi ve kaydedildi.' })
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
  settingsPasswordDialog.value = true
}

function openConnectionSettings() {
  Object.assign(connection, getStoredConnection())
  showConnection.value = true
}

function clearConnectionDraft() {
  Object.assign(connection, { url: '', publishableKey: '', source: 'none' })
}

function openPasswordReset() {
  resetEmail.value = email.value
  passwordResetDialog.value = true
}

async function sendPasswordReset() {
  if (!resetEmail.value) {
    $q.notify({ type: 'warning', message: 'E-posta adresini gir.' })
    return
  }

  try {
    await auth.sendPasswordReset(resetEmail.value)
    passwordResetDialog.value = false
    $q.notify({
      type: 'positive',
      message: 'Şifre yenileme bağlantısı gönderildi. Gelen kutunu kontrol et.',
    })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Bağlantı gönderilemedi.',
    })
  }
}
</script>
