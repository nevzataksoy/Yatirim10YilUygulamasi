import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getSupabaseClient } from '@/services/supabase'
import { registerNativePush } from '@/services/pushNotifications'
import { useAuthStore } from './auth'
import { usePortfolioStore } from './portfolio'
import { useUiStore } from './ui'

export const NOTIFICATION_EVENT_TYPES = [
  { label: 'Günlük Portföy Özeti', value: 'PORTFOLIO_DAILY' },
  { label: 'Yeni Sinyal Oluştu', value: 'SIGNAL_CREATED' },
]

export const useNotificationsStore = defineStore('notifications', () => {
  const providerSettings = ref(null)
  const devices = ref([])
  const templates = ref([])
  const messages = ref([])
  const logs = ref([])
  const loading = ref(false)
  const registering = ref(false)
  const lastError = ref('')
  const auth = useAuthStore()
  const portfolio = usePortfolioStore()
  const ui = useUiStore()

  const unreadCount = computed(() => messages.value.filter((item) => !item.read_at).length)
  const enabledTemplates = computed(() => templates.value.filter((item) => item.enabled))

  async function sync() {
    if (!auth.authenticated || auth.isDemo) return
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) return
    loading.value = true
    lastError.value = ''
    try {
      const userId = auth.user.id
      const [settingsResult, devicesResult, templatesResult, messagesResult, logsResult] = await Promise.all([
        client.from('push_provider_settings').select('*').eq('user_id', userId).maybeSingle(),
        client.from('notification_devices').select('*').eq('user_id', userId).order('last_seen_at', { ascending: false }),
        client.from('notification_templates').select('*').eq('user_id', userId).order('created_at'),
        client.from('notification_messages').select('*').eq('user_id', userId).order('created_at', { ascending: false }).limit(100),
        client.from('notification_logs').select('*').eq('user_id', userId).order('created_at', { ascending: false }).limit(200),
      ])
      for (const result of [settingsResult, devicesResult, templatesResult, messagesResult, logsResult]) {
        if (result.error) throw result.error
      }
      providerSettings.value = settingsResult.data || null
      devices.value = devicesResult.data || []
      templates.value = templatesResult.data || []
      messages.value = messagesResult.data || []
      logs.value = logsResult.data || []
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : 'Bildirim verileri alınamadı.'
      throw error
    } finally { loading.value = false }
  }

  async function saveProviderSettings(input) {
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')
    const payload = {
      user_id: auth.user.id,
      provider: 'FCM',
      enabled: Boolean(input.enabled),
      firebase_project_id: input.firebase_project_id || null,
      sender_id: input.sender_id || null,
      android_package_name: input.android_package_name || 'tr.rosayazilim.yatirimdashboard',
      web_vapid_key: input.web_vapid_key || null,
      note: input.note || null,
    }
    const { data, error } = await client
      .from('push_provider_settings')
      .upsert(payload, { onConflict: 'user_id' })
      .select()
      .single()
    if (error) throw error
    providerSettings.value = data
    return data
  }

  async function registerCurrentDevice() {
    if (auth.isDemo) throw new Error('Demo modunda cihaz kaydı yapılamaz.')
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')
    registering.value = true
    try {
      const registration = await registerNativePush({
        onReceived: async () => { await sync() },
        onAction: async (action) => {
          await sync()
          const messageId = action?.notification?.data?.message_id
          if (messageId) await markRead(messageId)
        },
      })
      if (!registration.supported) throw new Error('Push bildirim kaydı yalnız Capacitor mobil uygulamada kullanılabilir.')

      const payload = {
        user_id: auth.user.id,
        installation_id: registration.installationId || `permission-${Date.now()}`,
        device_name: registration.deviceName || null,
        platform: registration.platform || 'unknown',
        operating_system: registration.operatingSystem || null,
        os_version: registration.osVersion || null,
        app_version: registration.appVersion || null,
        target_kind: registration.targetKind || 'TOKEN',
        push_target: registration.pushTarget || null,
        permission_status: registration.permissionStatus,
        is_active: registration.permissionStatus === 'GRANTED',
        last_seen_at: new Date().toISOString(),
        metadata: registration.metadata || {},
      }
      const { data, error } = await client
        .from('notification_devices')
        .upsert(payload, { onConflict: 'user_id,installation_id' })
        .select()
        .single()
      if (error) throw error
      devices.value = [data, ...devices.value.filter((item) => item.id !== data.id)]
      return data
    } finally { registering.value = false }
  }

  async function setDeviceActive(id, active) {
    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yok.')
    const { data, error } = await client.from('notification_devices').update({ is_active: Boolean(active) }).eq('id', id).select().single()
    if (error) throw error
    devices.value = devices.value.map((item) => (item.id === id ? data : item))
    return data
  }

  async function saveTemplate(input) {
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')
    const eventType = input.event_type || 'PORTFOLIO_DAILY'
    const payload = {
      user_id: auth.user.id,
      account_id: eventType === 'PORTFOLIO_DAILY' ? input.account_id || portfolio.selectedAccountId : null,
      name: String(input.name || '').trim(),
      event_type: eventType,
      enabled: input.enabled !== false,
      timezone: input.timezone || 'Europe/Istanbul',
      schedule_time: eventType === 'PORTFOLIO_DAILY' ? input.schedule_time || '09:00' : null,
      days_of_week: input.days_of_week?.length ? input.days_of_week : [1,2,3,4,5,6,7],
      display_currency: input.display_currency || ui.displayAsset || 'USD',
      title_template: input.title_template || (eventType === 'PORTFOLIO_DAILY' ? 'Günlük Portföy Özeti' : 'Yeni yatırım sinyali'),
      body_template: input.body_template || (eventType === 'PORTFOLIO_DAILY'
        ? 'Portföy değeri: {{portfolio_value}} {{display_currency}}'
        : '{{system}} için {{direction}} sinyali oluştu. Edge {{edge}}, güven {{confidence}}.'),
      payload: input.payload || {},
    }
    if (!payload.name) throw new Error('Şablon adı zorunlu.')

    let query
    if (input.id) query = client.from('notification_templates').update(payload).eq('id', input.id)
    else query = client.from('notification_templates').insert(payload)
    const { data, error } = await query.select().single()
    if (error) throw error
    templates.value = [data, ...templates.value.filter((item) => item.id !== data.id)]
    return data
  }

  async function setTemplateEnabled(id, enabled) {
    const current = templates.value.find((item) => item.id === id)
    if (!current) throw new Error('Şablon bulunamadı.')
    return saveTemplate({ ...current, enabled })
  }

  async function deleteTemplate(id) {
    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yok.')
    const { error } = await client.from('notification_templates').delete().eq('id', id)
    if (error) throw error
    templates.value = templates.value.filter((item) => item.id !== id)
  }

  async function markRead(id) {
    const client = getSupabaseClient()
    if (!client) return
    const readAt = new Date().toISOString()
    const { error } = await client.from('notification_messages').update({ read_at: readAt }).eq('id', id)
    if (error) throw error
    messages.value = messages.value.map((item) => (item.id === id ? { ...item, read_at: readAt } : item))
  }

  async function markAllRead() {
    const client = getSupabaseClient()
    if (!client || !auth.user?.id || unreadCount.value === 0) return
    const readAt = new Date().toISOString()
    const { error } = await client
      .from('notification_messages')
      .update({ read_at: readAt })
      .eq('user_id', auth.user.id)
      .is('read_at', null)
    if (error) throw error
    messages.value = messages.value.map((item) => ({ ...item, read_at: item.read_at || readAt }))
  }

  function reset() {
    providerSettings.value = null
    devices.value = []
    templates.value = []
    messages.value = []
    logs.value = []
    lastError.value = ''
  }

  return {
    providerSettings, devices, templates, messages, logs, loading, registering, lastError,
    unreadCount, enabledTemplates, sync, saveProviderSettings, registerCurrentDevice,
    setDeviceActive, saveTemplate, setTemplateEnabled, deleteTemplate, markRead, markAllRead, reset,
  }
})
