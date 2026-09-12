import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  consumeAuthCallbackUrl,
  getAuthCallbackUrl,
  getConnectionSignature,
  getStoredConnection,
  getSupabaseClient,
  resetSupabaseClient,
  saveStoredConnection,
  testAuthenticatedSupabaseAccess,
  testSupabaseConnection,
} from '@/services/supabase'
import { asSupabaseAppError } from '@/services/supabaseErrors'

function mapUser(user) {
  if (!user) return null
  return {
    id: user.id,
    email: user.email || '',
    firstName: user.user_metadata?.first_name || '',
    middleName: user.user_metadata?.middle_name || '',
    lastName: user.user_metadata?.last_name || '',
  }
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref(null)
  const cachedUser = ref(null)
  const demoSession = ref(null)
  const ready = ref(false)
  const loading = ref(false)
  const lastError = ref('')
  const lastAuthEvent = ref('')
  const recoveryMode = ref(false)
  const connectionHealth = ref({
    status: 'idle',
    authApi: 'unknown',
    authenticatedRls: 'not_tested',
    latencyMs: null,
    checkedAt: null,
    message: 'Bağlantı henüz test edilmedi.',
  })
  let authSubscription = null
  let boundClient = null
  let initPromise = null

  const isDemo = computed(() => Boolean(demoSession.value?.active))
  const authenticated = computed(() => isDemo.value || Boolean(session.value?.user))
  const user = computed(() => {
    if (demoSession.value?.active) return demoSession.value.user
    return mapUser(session.value?.user) || cachedUser.value
  })

  function applySession(nextSession) {
    session.value = nextSession
    cachedUser.value = mapUser(nextSession?.user)
  }

  function applyUser(nextUser) {
    if (session.value && nextUser) session.value = { ...session.value, user: nextUser }
    cachedUser.value = mapUser(nextUser) || cachedUser.value
  }

  function applyError(error, fallback) {
    const wrapped = asSupabaseAppError(error, fallback)
    lastError.value = wrapped.message
    return wrapped
  }

  function applyAuthEvent(event, nextSession) {
    lastAuthEvent.value = event

    if (event === 'SIGNED_OUT') {
      recoveryMode.value = false
      applySession(null)
      return
    }

    if (event === 'PASSWORD_RECOVERY') recoveryMode.value = true
    if (nextSession) {
      demoSession.value = null
      applySession(nextSession)
    }

    if (event === 'TOKEN_REFRESHED' || event === 'SIGNED_IN') lastError.value = ''
  }

  function unbindAuthListener() {
    authSubscription?.unsubscribe()
    authSubscription = null
    boundClient = null
  }

  function bindAuthListener(client) {
    if (boundClient === client && authSubscription) return
    unbindAuthListener()
    const { data } = client.auth.onAuthStateChange((event, nextSession) => {
      applyAuthEvent(event, nextSession)
    })
    authSubscription = data.subscription
    boundClient = client
  }

  function setConnectionError(error, fallback) {
    const wrapped = applyError(error, fallback)
    connectionHealth.value = {
      status: 'error',
      authApi: wrapped.kind === 'RLS_DENIED' ? 'ok' : 'error',
      authenticatedRls: wrapped.kind === 'RLS_DENIED' ? 'error' : 'not_tested',
      latencyMs: null,
      checkedAt: new Date().toISOString(),
      message: wrapped.message,
      kind: wrapped.kind,
      retryable: wrapped.retryable,
    }
    return wrapped
  }

  async function verifyAuthenticatedAccess(client, activeSession) {
    if (!activeSession?.user?.id) return null
    try {
      const result = await testAuthenticatedSupabaseAccess(client, activeSession.user.id)
      connectionHealth.value = result
      return result
    } catch (error) {
      throw setConnectionError(error, 'Auth/RLS bağlantı testi başarısız.')
    }
  }

  async function runConnectionTest(config = getStoredConnection(), { includeSession = true } = {}) {
    loading.value = true
    lastError.value = ''
    try {
      const result = await testSupabaseConnection(config)
      const isActiveConfig =
        getConnectionSignature(config) === getConnectionSignature(getStoredConnection())
      if (includeSession && isActiveConfig && session.value?.user) {
        const activeClient = getSupabaseClient()
        const authenticatedResult = await verifyAuthenticatedAccess(activeClient, session.value)
        connectionHealth.value = {
          ...result,
          ...authenticatedResult,
          latencyMs: result.latencyMs + authenticatedResult.latencyMs,
        }
      } else {
        connectionHealth.value = result
      }
      return connectionHealth.value
    } catch (error) {
      throw setConnectionError(error, 'Supabase bağlantı testi başarısız.')
    } finally {
      loading.value = false
    }
  }

  async function performInit(force = false) {
    const client = getSupabaseClient()

    if (!force && ready.value && boundClient === client) return
    ready.value = false

    if (!client) {
      unbindAuthListener()
      applySession(null)
      connectionHealth.value = {
        status: 'unconfigured',
        authApi: 'unknown',
        authenticatedRls: 'not_tested',
        latencyMs: null,
        checkedAt: null,
        message: 'Supabase bağlantısı yapılandırılmamış.',
      }
      ready.value = true
      return
    }

    bindAuthListener(client)

    try {
      const { data, error } = await client.auth.getSession()
      if (error) throw error
      applySession(data.session)

      if (data.session?.user) {
        await runConnectionTest(getStoredConnection(), { includeSession: true })
      } else {
        await runConnectionTest(getStoredConnection(), { includeSession: false })
      }
    } catch (error) {
      setConnectionError(error, 'Supabase oturumu başlatılamadı.')
    } finally {
      ready.value = true
    }
  }

  async function init(options = {}) {
    const force = Boolean(options?.force)
    if (!force && initPromise) return initPromise
    initPromise = performInit(force).finally(() => {
      initPromise = null
    })
    return initPromise
  }

  async function configureConnection(config) {
    const current = getStoredConnection()
    const nextSignature = getConnectionSignature(config)
    const currentSignature = getConnectionSignature(current)
    const changed = nextSignature !== currentSignature

    await runConnectionTest(config, { includeSession: !changed })

    if (current.source === 'env' && changed) {
      throw new Error(
        'Ortam değişkeniyle gelen Supabase bağlantısı uygulama içinden değiştirilemez.',
      )
    }

    if (!changed) return { changed: false, health: connectionHealth.value }

    loading.value = true
    try {
      const previousClient = getSupabaseClient()
      unbindAuthListener()
      if (previousClient && session.value) {
        await previousClient.auth.signOut({ scope: 'local' })
      }
      await resetSupabaseClient()
      saveStoredConnection(config)
      demoSession.value = null
      recoveryMode.value = false
      applySession(null)
      ready.value = false
      await init({ force: true })
      return { changed: true, health: connectionHealth.value }
    } finally {
      loading.value = false
    }
  }

  async function signIn(email, password) {
    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yapılandırılmamış.')

    loading.value = true
    lastError.value = ''
    try {
      const { data, error } = await client.auth.signInWithPassword({ email, password })
      if (error) throw error
      demoSession.value = null
      applySession(data.session)
      await verifyAuthenticatedAccess(client, data.session)
    } catch (error) {
      try {
        await client.auth.signOut({ scope: 'local' })
      } catch {
        // The local store is cleared below even when the network is unavailable.
      }
      applySession(null)
      throw applyError(error, 'Giriş başarısız.')
    } finally {
      loading.value = false
    }
  }

  async function signUp(email, password, firstName, lastName) {
    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yapılandırılmamış.')

    loading.value = true
    try {
      const { data, error } = await client.auth.signUp({
        email,
        password,
        options: {
          data: { first_name: firstName, last_name: lastName },
          emailRedirectTo: getAuthCallbackUrl('confirmation'),
        },
      })
      if (error) throw error
      if (data.session) {
        applySession(data.session)
        await verifyAuthenticatedAccess(client, data.session)
      }
      return data
    } catch (error) {
      if (session.value) {
        try {
          await client.auth.signOut({ scope: 'local' })
        } catch {
          // The local store is cleared below even when the network is unavailable.
        }
        applySession(null)
      }
      throw applyError(error, 'Hesap oluşturulamadı.')
    } finally {
      loading.value = false
    }
  }

  async function sendPasswordReset(email) {
    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yapılandırılmamış.')
    loading.value = true
    lastError.value = ''
    try {
      const { error } = await client.auth.resetPasswordForEmail(email, {
        redirectTo: getAuthCallbackUrl('recovery'),
      })
      if (error) throw error
    } catch (error) {
      throw applyError(error, 'Şifre sıfırlama bağlantısı gönderilemedi.')
    } finally {
      loading.value = false
    }
  }

  function demoLogin() {
    demoSession.value = {
      active: true,
      user: {
        id: 'demo-user',
        email: 'demo@rosa.local',
        firstName: 'Demo',
        middleName: '',
        lastName: 'Yatırımcı',
      },
    }
    session.value = null
    cachedUser.value = demoSession.value.user
    ready.value = true
  }

  async function signOut() {
    const client = getSupabaseClient()
    loading.value = true
    try {
      if (client && session.value) {
        const { error } = await client.auth.signOut()
        if (error) throw error
      }
    } catch (error) {
      lastError.value = asSupabaseAppError(error, 'Oturum sunucuda kapatılamadı.').message
    } finally {
      demoSession.value = null
      recoveryMode.value = false
      applySession(null)
      loading.value = false
    }
  }

  async function getProfile() {
    if (!user.value) throw new Error('Profil için aktif oturum gerekli.')
    if (isDemo.value) return { ...user.value }

    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yapılandırılmamış.')
    const { data, error } = await client
      .from('profiles')
      .select('first_name,middle_name,last_name')
      .eq('user_id', user.value.id)
      .maybeSingle()
    if (error) throw error

    return {
      ...user.value,
      firstName: data?.first_name ?? user.value.firstName ?? '',
      middleName: data?.middle_name ?? user.value.middleName ?? '',
      lastName: data?.last_name ?? user.value.lastName ?? '',
    }
  }

  async function updateProfile({ firstName, middleName, lastName, email }) {
    if (!user.value) throw new Error('Profil için aktif oturum gerekli.')
    const normalized = {
      firstName: String(firstName || '').trim(),
      middleName: String(middleName || '').trim(),
      lastName: String(lastName || '').trim(),
      email: String(email || '').trim(),
    }

    if (isDemo.value) {
      demoSession.value = {
        ...demoSession.value,
        user: { ...demoSession.value.user, ...normalized },
      }
      cachedUser.value = demoSession.value.user
      return { ...demoSession.value.user, emailConfirmationPending: false }
    }

    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yapılandırılmamış.')
    const emailChanged = normalized.email && normalized.email !== user.value.email
    const authPayload = {
      data: {
        first_name: normalized.firstName,
        middle_name: normalized.middleName,
        last_name: normalized.lastName,
      },
    }
    if (emailChanged) authPayload.email = normalized.email

    const { data: authData, error: authError } = await client.auth.updateUser(authPayload)
    if (authError) throw authError

    const { error: profileError } = await client.from('profiles').upsert(
      {
        user_id: user.value.id,
        first_name: normalized.firstName || null,
        middle_name: normalized.middleName || null,
        last_name: normalized.lastName || null,
      },
      { onConflict: 'user_id' },
    )
    if (profileError) throw profileError

    applyUser(authData.user)
    return {
      ...mapUser(authData.user),
      emailConfirmationPending: emailChanged && authData.user?.email !== normalized.email,
    }
  }

  async function updatePassword(password) {
    if (!user.value) throw new Error('Şifre güncellemek için aktif oturum gerekli.')
    if (String(password || '').length < 8) throw new Error('Yeni şifre en az 8 karakter olmalı.')
    if (isDemo.value) return

    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yapılandırılmamış.')
    const { data, error } = await client.auth.updateUser({ password })
    if (error) throw error
    applyUser(data.user)
    recoveryMode.value = false
    lastAuthEvent.value = 'USER_UPDATED'
  }

  function finishRecovery() {
    recoveryMode.value = false
  }

  async function consumeCallback(callbackUrl) {
    const result = await consumeAuthCallbackUrl(callbackUrl)
    if (result.flow === 'recovery') recoveryMode.value = true
    await init({ force: true })
    return result
  }

  function dispose() {
    unbindAuthListener()
    ready.value = false
  }

  return {
    session,
    cachedUser,
    demoSession,
    ready,
    loading,
    lastError,
    lastAuthEvent,
    recoveryMode,
    connectionHealth,
    isDemo,
    authenticated,
    user,
    init,
    runConnectionTest,
    configureConnection,
    signIn,
    signUp,
    sendPasswordReset,
    demoLogin,
    getProfile,
    updateProfile,
    updatePassword,
    finishRecovery,
    consumeCallback,
    signOut,
    dispose,
  }
})
