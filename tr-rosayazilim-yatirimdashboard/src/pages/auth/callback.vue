<template>
  <q-layout view="hHh lpR fFf" class="login-layout">
    <q-page-container>
      <q-page class="login-page flex flex-center q-pa-md">
        <q-card class="login-card" flat>
          <q-card-section class="q-pa-lg">
            <AppLogo />
            <div class="text-h5 text-weight-bold q-mt-xl">{{ title }}</div>
            <div class="text-body2 text-grey-7 q-mt-sm">{{ description }}</div>

            <div v-if="processing" class="row items-center q-gutter-md q-mt-xl">
              <q-spinner color="primary" size="32px" />
              <span>Supabase dönüş bağlantısı doğrulanıyor…</span>
            </div>

            <q-banner v-else-if="errorMessage" rounded class="bg-red-1 text-negative q-mt-lg">
              <template #avatar><q-icon name="error" /></template>
              {{ errorMessage }}
            </q-banner>

            <q-form v-else-if="isRecovery" class="q-mt-lg" @submit.prevent="updatePassword">
              <q-input
                v-model="password"
                outlined
                :type="showPassword ? 'text' : 'password'"
                label="Yeni şifre"
                autocomplete="new-password"
                :rules="[(value) => value.length >= 8 || 'En az 8 karakter']"
              >
                <template #prepend><q-icon name="lock_reset" /></template>
                <template #append>
                  <q-icon
                    :name="showPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showPassword = !showPassword"
                  />
                </template>
              </q-input>
              <q-input
                v-model="passwordConfirmation"
                outlined
                :type="showPassword ? 'text' : 'password'"
                label="Yeni şifre tekrarı"
                autocomplete="new-password"
                class="q-mt-sm"
                :rules="[(value) => value === password || 'Şifreler eşleşmiyor']"
              />
              <q-btn
                push
                color="primary"
                size="lg"
                class="full-width q-mt-md"
                label="Şifreyi Güncelle"
                type="submit"
                no-caps
                :loading="saving"
              />
            </q-form>

            <q-banner v-else rounded class="bg-green-1 text-green-10 q-mt-lg">
              <template #avatar><q-icon name="verified" /></template>
              E-posta adresin doğrulandı ve oturum güvenli biçimde başlatıldı.
            </q-banner>

            <q-btn
              v-if="!processing && (!isRecovery || errorMessage)"
              push
              color="primary"
              class="full-width q-mt-lg"
              :label="auth.authenticated ? 'Uygulamaya Devam Et' : 'Giriş Ekranına Dön'"
              no-caps
              @click="continueToApp"
            />
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import AppLogo from '@/components/AppLogo.vue'
import { useAuthStore } from '@/stores/auth'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const portfolio = usePortfolioStore()
const engine = useEngineStore()

const processing = ref(true)
const saving = ref(false)
const password = ref('')
const passwordConfirmation = ref('')
const showPassword = ref(false)
const errorMessage = ref('')

const isRecovery = computed(
  () =>
    route.query.flow === 'recovery' ||
    auth.recoveryMode ||
    auth.lastAuthEvent === 'PASSWORD_RECOVERY',
)
const title = computed(() => (isRecovery.value ? 'Yeni şifreni belirle' : 'E-posta doğrulaması'))
const description = computed(() =>
  isRecovery.value
    ? 'Yeni şifreni kaydettikten sonra mevcut güvenli oturumunla uygulamaya devam edebilirsin.'
    : 'Doğrulama bağlantısı Supabase Auth tarafından işleniyor.',
)

onMounted(async () => {
  try {
    await auth.init({ force: true })
    if (auth.connectionHealth.status === 'error') {
      errorMessage.value = auth.connectionHealth.message
    } else if (!auth.authenticated) {
      errorMessage.value =
        auth.lastError || 'Doğrulama bağlantısı geçersiz, süresi dolmuş veya daha önce kullanılmış.'
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Auth bağlantısı işlenemedi.'
  } finally {
    processing.value = false
  }
})

async function updatePassword() {
  if (password.value.length < 8 || password.value !== passwordConfirmation.value) return

  saving.value = true
  try {
    await auth.updatePassword(password.value)
    auth.finishRecovery()
    await Promise.allSettled([portfolio.sync(), engine.sync()])
    $q.notify({ type: 'positive', message: 'Şifren güncellendi.' })
    await router.replace('/')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Şifre güncellenemedi.'
  } finally {
    saving.value = false
  }
}

async function continueToApp() {
  auth.finishRecovery()
  if (auth.authenticated) {
    await Promise.allSettled([portfolio.sync(), engine.sync()])
    await router.replace('/')
  } else {
    await router.replace('/login')
  }
}
</script>
