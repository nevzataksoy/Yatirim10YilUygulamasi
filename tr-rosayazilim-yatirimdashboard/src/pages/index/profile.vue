<template>
  <q-page>
    <div class="page-wrap">
      <div class="q-mb-lg">
        <div class="page-title">Profilim</div>
        <div class="page-subtitle q-mt-xs">
          Hesap sahibinin ad, e-posta ve oturum şifresi bilgilerini güvenli biçimde güncelle.
        </div>
      </div>

      <q-banner v-if="auth.isDemo" rounded class="bg-amber-1 text-amber-10 q-mb-lg">
        <template #avatar><q-icon name="science" /></template>
        Demo modundaki profil değişiklikleri yalnız bu cihazdaki demo oturumunda saklanır; Supabase
        Auth'a gönderilmez.
      </q-banner>

      <div class="row q-col-gutter-lg">
        <div class="col-12 col-lg-7">
          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Kişisel Bilgiler</div>
              <div class="text-caption text-grey-7">
                Ad bilgileri profil kaydında ve Supabase kullanıcı metadata alanında birlikte
                güncellenir.
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section>
              <q-form class="row q-col-gutter-md" @submit.prevent="saveProfile">
                <div class="col-12 col-sm-4">
                  <q-input
                    v-model.trim="profile.firstName"
                    outlined
                    label="Ad"
                    :rules="[(value) => Boolean(value) || 'Ad gerekli']"
                  />
                </div>
                <div class="col-12 col-sm-4">
                  <q-input v-model.trim="profile.middleName" outlined label="İkinci Ad" />
                </div>
                <div class="col-12 col-sm-4">
                  <q-input
                    v-model.trim="profile.lastName"
                    outlined
                    label="Soyad"
                    :rules="[(value) => Boolean(value) || 'Soyad gerekli']"
                  />
                </div>
                <div class="col-12">
                  <q-input
                    v-model.trim="profile.email"
                    outlined
                    type="email"
                    label="E-posta"
                    autocomplete="email"
                    :rules="[(value) => /.+@.+\..+/.test(value) || 'Geçerli bir e-posta yaz']"
                  >
                    <template #prepend><q-icon name="mail" /></template>
                  </q-input>
                  <div class="text-caption text-grey-6 q-mt-xs">
                    E-posta değişikliğinde Supabase ayarına göre yeni ve/veya eski adrese doğrulama
                    bağlantısı gönderilebilir.
                  </div>
                </div>
                <div class="col-12 row justify-end q-gutter-sm">
                  <q-btn
                    push
                    color="grey-3"
                    text-color="grey-9"
                    icon="undo"
                    label="Vazgeç"
                    no-caps
                    :disable="savingProfile"
                    @click="loadProfile"
                  />
                  <q-btn
                    push
                    color="primary"
                    icon="save"
                    label="Profili Kaydet"
                    no-caps
                    type="submit"
                    :loading="savingProfile"
                  />
                </div>
              </q-form>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-lg-5">
          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Şifreyi Güncelle</div>
              <div class="text-caption text-grey-7">
                Yeni şifre en az 8 karakter olmalı. Şifre uygulamanın yerel saklama alanına
                yazılmaz.
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section>
              <q-form @submit.prevent="savePassword">
                <q-input
                  v-model="password.next"
                  outlined
                  :type="showPassword ? 'text' : 'password'"
                  label="Yeni Şifre"
                  autocomplete="new-password"
                  :rules="[(value) => value.length >= 8 || 'En az 8 karakter']"
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
                <q-input
                  v-model="password.confirm"
                  outlined
                  :type="showPassword ? 'text' : 'password'"
                  label="Yeni Şifre Tekrar"
                  autocomplete="new-password"
                  class="q-mt-sm"
                  :rules="[(value) => value === password.next || 'Şifreler aynı değil']"
                >
                  <template #prepend><q-icon name="verified_user" /></template>
                </q-input>
                <div class="row justify-end q-gutter-sm q-mt-md">
                  <q-btn
                    push
                    color="grey-3"
                    text-color="grey-9"
                    icon="backspace"
                    label="Temizle"
                    no-caps
                    :disable="savingPassword"
                    @click="clearPassword"
                  />
                  <q-btn
                    push
                    color="primary"
                    icon="password"
                    label="Şifreyi Güncelle"
                    no-caps
                    type="submit"
                    :loading="savingPassword"
                  />
                </div>
              </q-form>
            </q-card-section>
          </q-card>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'

const $q = useQuasar()
const auth = useAuthStore()
const savingProfile = ref(false)
const savingPassword = ref(false)
const showPassword = ref(false)
const profile = reactive({ firstName: '', middleName: '', lastName: '', email: '' })
const password = reactive({ next: '', confirm: '' })

async function loadProfile() {
  try {
    const current = await auth.getProfile()
    profile.firstName = current.firstName || ''
    profile.middleName = current.middleName || ''
    profile.lastName = current.lastName || ''
    profile.email = current.email || ''
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Profil yüklenemedi.',
    })
  }
}

async function saveProfile() {
  savingProfile.value = true
  try {
    const result = await auth.updateProfile(profile)
    await loadProfile()
    $q.notify({
      type: 'positive',
      message: result.emailConfirmationPending
        ? 'Profil kaydedildi. E-posta değişikliğini gelen doğrulama bağlantısından tamamla.'
        : 'Profil bilgileri güncellendi.',
    })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Profil güncellenemedi.',
    })
  } finally {
    savingProfile.value = false
  }
}

function clearPassword() {
  password.next = ''
  password.confirm = ''
}

async function savePassword() {
  if (password.next !== password.confirm) {
    $q.notify({ type: 'warning', message: 'Yeni şifreler aynı değil.' })
    return
  }

  savingPassword.value = true
  try {
    await auth.updatePassword(password.next)
    clearPassword()
    $q.notify({
      type: 'positive',
      message: auth.isDemo
        ? 'Demo şifre formu doğrulandı; Supabase değişikliği yapılmadı.'
        : 'Şifre güncellendi.',
    })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Şifre güncellenemedi.',
    })
  } finally {
    savingPassword.value = false
  }
}

onMounted(loadProfile)
</script>
