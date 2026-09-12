<template>
  <q-dialog
    :model-value="modelValue"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card class="settings-password-card">
      <q-form @submit.prevent="submit">
        <q-card-section class="row items-start no-wrap q-gutter-md">
          <q-avatar color="primary" text-color="white" icon="admin_panel_settings" />
          <div>
            <div class="text-h6 text-weight-bold">
              {{ setupMode ? 'Ayar şifresi oluştur' : 'Bağlantı ayarlarını aç' }}
            </div>
            <div class="text-body2 text-grey-7 q-mt-xs">
              {{
                setupMode
                  ? 'Supabase bağlantı ayarlarını bu cihazda korumak için bir şifre belirle.'
                  : 'Supabase bağlantı ayarlarına erişmek için ayar şifresini gir.'
              }}
            </div>
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section>
          <q-banner v-if="errorMessage" rounded class="bg-red-1 text-negative q-mb-md">
            {{ errorMessage }}
          </q-banner>

          <q-input
            ref="passwordInput"
            v-model="password"
            outlined
            :type="showPassword ? 'text' : 'password'"
            :label="setupMode ? 'Yeni ayar şifresi' : 'Ayar şifresi'"
            :autocomplete="setupMode ? 'new-password' : 'current-password'"
            :rules="[
              (value) =>
                String(value || '').length >= MIN_SETTINGS_PASSWORD_LENGTH ||
                `En az ${MIN_SETTINGS_PASSWORD_LENGTH} karakter`,
            ]"
            autofocus
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
            v-if="setupMode"
            v-model="confirmation"
            outlined
            :type="showPassword ? 'text' : 'password'"
            label="Ayar şifresini doğrula"
            autocomplete="new-password"
            class="q-mt-sm"
            :rules="[(value) => value === password || 'Şifreler aynı değil']"
          >
            <template #prepend><q-icon name="verified_user" /></template>
          </q-input>

          <div v-if="setupMode" class="text-caption text-grey-7 q-mt-sm">
            Şifrenin kendisi kaydedilmez; tek yönlü doğrulayıcı SecureLS içinde saklanır.
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right" class="popup-action-footer q-pa-md">
          <q-btn
            push
            color="grey-3"
            text-color="grey-9"
            label="Vazgeç"
            no-caps
            :disable="loading"
            @click="close"
          />
          <q-btn
            push
            color="primary"
            :icon="setupMode ? 'password' : 'lock_open'"
            :label="setupMode ? 'Şifreyi Kaydet' : 'Ayarları Aç'"
            type="submit"
            no-caps
            :loading="loading"
          />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  hasSettingsPassword,
  MIN_SETTINGS_PASSWORD_LENGTH,
  setSettingsPassword,
  verifySettingsPassword,
} from '@/services/settingsPassword'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  forceSetup: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'verified'])

const password = ref('')
const confirmation = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const passwordConfigured = ref(hasSettingsPassword())
const passwordInput = ref(null)
const setupMode = computed(() => props.forceSetup || !passwordConfigured.value)

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (!isOpen) return
    passwordConfigured.value = hasSettingsPassword()
    password.value = ''
    confirmation.value = ''
    showPassword.value = false
    errorMessage.value = ''
    await nextTick()
    passwordInput.value?.focus()
  },
)

function close() {
  if (loading.value) return
  emit('update:modelValue', false)
}

async function submit() {
  errorMessage.value = ''
  loading.value = true
  const wasSetup = setupMode.value

  try {
    if (wasSetup) {
      if (password.value !== confirmation.value) {
        errorMessage.value = 'Ayar şifreleri aynı değil.'
        return
      }
      await setSettingsPassword(password.value)
      passwordConfigured.value = true
    } else {
      const verified = await verifySettingsPassword(password.value)
      if (!verified) {
        errorMessage.value = 'Ayar şifresi hatalı.'
        password.value = ''
        await nextTick()
        passwordInput.value?.focus()
        return
      }
    }

    emit('update:modelValue', false)
    emit('verified', { created: wasSetup })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Ayar şifresi doğrulanamadı.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.settings-password-card {
  width: min(520px, calc(100vw - 32px));
  max-width: 520px;
}
</style>
