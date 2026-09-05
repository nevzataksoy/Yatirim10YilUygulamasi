import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'
import { defineBoot } from '#q-app'
import { watch } from 'vue'
import { createDisplayQuoteScheduler } from '@/services/display-quotes/displayQuoteScheduler'
import { startAppRealtime, stopAppRealtime } from '@/services/realtime'
import { getSupabaseClient } from '@/services/supabase'
import { useAuthStore } from '@/stores/auth'
import { useDisplayQuoteStore } from '@/stores/displayQuotes'
import { useEngineStore } from '@/stores/engine'
import { useInstitutionsStore } from '@/stores/institutions'
import { useNotificationsStore } from '@/stores/notifications'
import { usePortfolioStore } from '@/stores/portfolio'

export default defineBoot(async ({ router, store }) => {
  const auth = useAuthStore(store)
  const portfolio = usePortfolioStore(store)
  const engine = useEngineStore(store)
  const institutions = useInstitutionsStore(store)
  const notifications = useNotificationsStore(store)
  const displayQuotes = useDisplayQuoteStore(store)
  const displayQuoteScheduler = createDisplayQuoteScheduler({
    quoteStore: displayQuotes,
    engineStore: engine,
  })

  const isPublicRoute = (path) => path === '/login' || path === '/auth/callback'
  displayQuotes.hydrateCache()

  async function syncAuthenticatedData() {
    if (!auth.authenticated) return
    await Promise.allSettled([
      portfolio.sync(),
      engine.sync(),
      institutions.sync(),
      notifications.sync(),
      notifications.bindNativeListeners(),
    ])
    displayQuotes.applySnapshotFallback(engine.market)
  }

  async function handleNativeAuthUrl(url) {
    if (!url) return
    try {
      const result = await auth.consumeCallback(url)
      await router.replace({ path: '/auth/callback', query: { flow: result.flow } })
    } catch {
      await router.replace({ path: '/auth/callback', query: { error: 'callback' } })
    }
  }

  await auth.init()

  if (Capacitor.isNativePlatform()) {
    App.addListener('appUrlOpen', ({ url }) => handleNativeAuthUrl(url))
    const launchUrl = await App.getLaunchUrl().catch(() => null)
    if (launchUrl?.url) await handleNativeAuthUrl(launchUrl.url)

    const client = getSupabaseClient()
    client?.auth.startAutoRefresh()

    App.addListener('appStateChange', async ({ isActive }) => {
      const activeClient = getSupabaseClient()
      if (!isActive) {
        activeClient?.auth.stopAutoRefresh()
        await displayQuoteScheduler.stop()
        await stopAppRealtime()
        return
      }

      activeClient?.auth.startAutoRefresh()
      await auth.init({ force: true })
      if (auth.authenticated) {
        await syncAuthenticatedData()
        displayQuoteScheduler.start()
        await startAppRealtime(store)
      } else {
        await displayQuoteScheduler.stop()
        await stopAppRealtime()
      }
    })
  }

  if (auth.authenticated) {
    await syncAuthenticatedData()
    displayQuoteScheduler.start()
    await startAppRealtime(store)
  }

  router.beforeEach(async (to) => {
    if (!auth.ready) await auth.init()

    if (to.path === '/login' && auth.authenticated && !auth.recoveryMode) return '/'
    if (!isPublicRoute(to.path) && !auth.authenticated) return '/login'

    if (auth.authenticated && !portfolio.lastSyncAt) {
      await syncAuthenticatedData()
      displayQuoteScheduler.start()
      await startAppRealtime(store)
    }

    return true
  })

  watch(
    () => auth.recoveryMode,
    (active) => {
      if (active && router.currentRoute.value.path !== '/auth/callback') {
        router.replace({ path: '/auth/callback', query: { flow: 'recovery' } })
      }
    },
  )

  watch(
    () => auth.authenticated,
    async (active) => {
      const currentPath = router.currentRoute.value.path
      if (!active) {
        await displayQuoteScheduler.stop()
        await stopAppRealtime()
        if (!isPublicRoute(currentPath)) await router.replace('/login')
        return
      }

      await syncAuthenticatedData()
      displayQuoteScheduler.start()
      await startAppRealtime(store)
      if (currentPath === '/login' && !auth.recoveryMode) await router.replace('/')
    },
  )
})
