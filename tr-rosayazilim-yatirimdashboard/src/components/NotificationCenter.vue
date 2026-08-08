<template>
  <q-drawer
    :model-value="modelValue"
    side="right"
    overlay
    bordered
    :width="360"
    class="bg-white"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="column fit">
      <div class="q-pa-md row items-center">
        <div>
          <div class="text-h6 text-weight-bold">Bildirimler</div>
          <div class="text-caption text-grey-7">Uygulama içi gelen kutusu</div>
        </div>
        <q-space />
        <q-btn
          flat
          round
          dense
          icon="done_all"
          :disable="!notifications.unreadCount"
          @click="markAllRead"
        >
          <q-tooltip>Tümünü okundu işaretle</q-tooltip>
        </q-btn>
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </div>
      <q-separator />

      <q-scroll-area class="col">
        <q-list separator>
          <q-item
            v-for="item in notifications.messages"
            :key="item.id"
            clickable
            :class="item.read_at ? '' : 'bg-blue-1'"
            @click="openMessage(item)"
          >
            <q-item-section avatar>
              <q-avatar
                :color="item.read_at ? 'grey-2' : 'primary'"
                :text-color="item.read_at ? 'grey-7' : 'white'"
                :icon="item.event_type === 'SIGNAL_CREATED' ? 'insights' : 'notifications'"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-bold">{{ item.title }}</q-item-label>
              <q-item-label caption lines="3">{{ item.body }}</q-item-label>
              <q-item-label caption class="q-mt-xs">{{ formatDate(item.created_at) }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="!notifications.messages.length && !notifications.loading">
            <q-item-section class="text-grey-7">Henüz bildirim yok.</q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>

      <q-separator />
      <div class="q-pa-sm">
        <q-btn
          flat
          color="primary"
          icon="tune"
          label="Bildirim Yönetimi"
          to="/notifications"
          no-caps
          class="full-width"
          @click="emit('update:modelValue', false)"
        />
      </div>
    </div>
  </q-drawer>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue'])
const auth = useAuthStore()
const notifications = useNotificationsStore()
const router = useRouter()

function formatDate(value) {
  return value ? new Date(value).toLocaleString('tr-TR') : '—'
}

async function markAllRead() {
  try {
    await notifications.markAllRead()
  } catch {
    // Inbox remains usable even if a read receipt cannot be persisted temporarily.
  }
}

async function openMessage(item) {
  if (!item.read_at) await notifications.markRead(item.id).catch(() => null)
  const route = item.payload?.route
  if (route) {
    emit('update:modelValue', false)
    await router.push(route)
  }
}

async function initialize() {
  if (!auth.authenticated || auth.isDemo) return
  try {
    await notifications.sync()
  } catch {
    // Notification infrastructure is optional and must never block app startup.
  }
}

onMounted(initialize)
watch(
  () => auth.authenticated,
  (value) => {
    if (value) initialize()
    else notifications.reset()
  },
)
</script>
