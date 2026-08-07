import { defineBoot } from '#q-app'
import { watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useEngineStore } from '@/stores/engine'
import { usePortfolioStore } from '@/stores/portfolio'

export default defineBoot(async ({ router, store }) => {
  const auth = useAuthStore(store)
  const portfolio = usePortfolioStore(store)
  const engine = useEngineStore(store)

  await auth.init()

  const isPublicRoute = (path) => path === '/login' || path === '/auth/callback'

  async function handleNativeAuthUrl(url) {
    if (!url) return
    try {
      const result = await auth.consumeCallback(url)
      await router.replace({ path: '/auth/callback', query: { flow: result.flow } })
    } catch {
      await router.replace({ path: '/auth/callback', query: { error: 'callback' } })
    }
  }

  const nativeApp = globalThis.window?.Capacitor?.Plugins?.App
  if (nativeApp?.addListener) {
    nativeApp.addListener('appUrlOpen', ({ url }) => handleNativeAuthUrl(url))
    const launchUrl = await nativeApp.getLaunchUrl?.()
    if (launchUrl?.url) await handleNativeAuthUrl(launchUrl.url)
  }

  if (auth.authenticated) {
    await Promise.allSettled([portfolio.sync(), engine.sync()])
  }

  router.beforeEach(async (to) => {
    if (!auth.ready) await auth.init()

    if (to.path === '/login' && auth.authenticated && !auth.recoveryMode) return '/'
    if (!isPublicRoute(to.path) && !auth.authenticated) return '/login'

    if (auth.authenticated && !portfolio.lastSyncAt) {
      await Promise.allSettled([portfolio.sync(), engine.sync()])
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
    (active) => {
      const currentPath = router.currentRoute.value.path
      if (!active && !isPublicRoute(currentPath)) router.replace('/login')
      if (active && currentPath === '/login' && !auth.recoveryMode) router.replace('/')
    },
  )
})
