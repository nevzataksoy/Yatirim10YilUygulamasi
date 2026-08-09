import { getSupabaseClient } from '@/services/supabase'
import { useAuthStore } from '@/stores/auth'
import { useEngineStore } from '@/stores/engine'
import { useInstitutionsStore } from '@/stores/institutions'
import { useNotificationsStore } from '@/stores/notifications'
import { usePortfolioStore } from '@/stores/portfolio'

let activeClient = null
let activeChannel = null
let activeUserId = ''
let engineStore = null
const syncTimers = new Map()

function scheduleSync(key, callback, delay = 180) {
  const previous = syncTimers.get(key)
  if (previous) clearTimeout(previous)
  const timer = setTimeout(() => {
    syncTimers.delete(key)
    Promise.resolve(callback()).catch(() => null)
  }, delay)
  syncTimers.set(key, timer)
}

function clearScheduledSyncs() {
  for (const timer of syncTimers.values()) clearTimeout(timer)
  syncTimers.clear()
}

function setRealtimeStatus(status) {
  engineStore?.setRealtimeStatus?.(status)
}

export async function stopAppRealtime() {
  clearScheduledSyncs()
  if (activeClient && activeChannel) {
    await activeClient.removeChannel(activeChannel).catch(() => null)
  }
  activeClient = null
  activeChannel = null
  activeUserId = ''
  setRealtimeStatus('CLOSED')
}

export async function startAppRealtime(store) {
  const client = getSupabaseClient()
  const auth = useAuthStore(store)
  const portfolio = usePortfolioStore(store)
  const engine = useEngineStore(store)
  const institutions = useInstitutionsStore(store)
  const notifications = useNotificationsStore(store)
  engineStore = engine

  const userId = auth.user?.id || ''
  if (!client || !auth.authenticated || auth.isDemo || !userId) {
    await stopAppRealtime()
    return null
  }

  if (activeClient === client && activeChannel && activeUserId === userId) return activeChannel

  await stopAppRealtime()
  activeClient = client
  activeUserId = userId

  const syncEngine = () => scheduleSync('engine', () => engine.sync())
  const syncPortfolio = () => scheduleSync('portfolio', () => portfolio.sync())
  const syncInstitutions = () => scheduleSync('institutions', () => institutions.sync())
  const syncNotifications = () => scheduleSync('notifications', () => notifications.sync())

  let channel = client.channel(`app-live-${userId}`)

  for (const table of ['market_snapshot', 'decision_snapshot', 'engine_health_snapshot', 'model_validation_snapshot']) {
    channel = channel.on('postgres_changes', { event: '*', schema: 'public', table }, syncEngine)
  }

  for (const table of ['investment_accounts', 'portfolio_transactions', 'user_investment_settings']) {
    channel = channel.on('postgres_changes', { event: '*', schema: 'public', table }, syncPortfolio)
  }

  for (const table of ['financial_institutions', 'investment_account_institutions']) {
    channel = channel.on('postgres_changes', { event: '*', schema: 'public', table }, syncInstitutions)
  }

  for (const table of [
    'push_provider_settings',
    'notification_devices',
    'notification_templates',
    'notification_messages',
    'notification_logs',
  ]) {
    channel = channel.on('postgres_changes', { event: '*', schema: 'public', table }, syncNotifications)
  }

  activeChannel = channel.subscribe((status) => {
    setRealtimeStatus(status)
    if (status === 'SUBSCRIBED') {
      syncEngine()
      syncPortfolio()
      syncInstitutions()
      syncNotifications()
    }
  })

  return activeChannel
}
