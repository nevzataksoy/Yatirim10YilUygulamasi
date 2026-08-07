import { createClient } from '@supabase/supabase-js'
import { getSecureValue, setSecureValue, supabaseSecureStorage } from './secureStorage.js'
import { asSupabaseAppError } from './supabaseErrors.js'

const CONNECTION_KEY = 'app:connection'
let client = null
let clientSignature = ''

function isServiceRoleKey(value) {
  if (value.startsWith('sb_secret_')) return true
  const parts = value.split('.')
  if (parts.length !== 3) return false

  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
    return JSON.parse(globalThis.atob(padded))?.role === 'service_role'
  } catch {
    return false
  }
}

export function normalizeSupabaseConnection(config) {
  const url = String(config?.url || '')
    .trim()
    .replace(/\/+$/, '')
  const publishableKey = String(config?.publishableKey || '').trim()

  if (!url || !publishableKey) {
    throw new Error('Project URL ve Publishable Key zorunludur.')
  }

  if (isServiceRoleKey(publishableKey)) {
    throw new Error('service_role veya secret key istemci uygulamasına kaydedilemez.')
  }

  let parsed
  try {
    parsed = new URL(url)
  } catch {
    throw new Error('Project URL geçerli bir URL olmalıdır.')
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('Project URL http veya https protokolü kullanmalıdır.')
  }

  return { url, publishableKey }
}

export function getConnectionSignature(config) {
  if (!config?.url || !config?.publishableKey) return ''
  const normalized = normalizeSupabaseConnection(config)
  return `${normalized.url}|${normalized.publishableKey}`
}

export function getStoredConnection() {
  const envUrl = import.meta.env?.QCLI_SUPABASE_URL?.trim() || ''
  const envKey = import.meta.env?.QCLI_SUPABASE_PUBLISHABLE_KEY?.trim() || ''
  if (envUrl && envKey) return { url: envUrl, publishableKey: envKey, source: 'env' }

  const stored = getSecureValue(CONNECTION_KEY, { url: '', publishableKey: '' })
  return { ...stored, source: stored.url && stored.publishableKey ? 'local' : 'none' }
}

export function saveStoredConnection(config) {
  const normalized = normalizeSupabaseConnection(config)
  setSecureValue(CONNECTION_KEY, normalized)
}

export function hasSupabaseConfig() {
  const config = getStoredConnection()
  return Boolean(config.url && config.publishableKey)
}

export function getSupabaseClient() {
  const config = getStoredConnection()
  if (!config.url || !config.publishableKey) return null

  const signature = getConnectionSignature(config)
  if (!client || signature !== clientSignature) {
    client = createClient(config.url, config.publishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: 'pkce',
        storage: supabaseSecureStorage,
      },
      realtime: { params: { eventsPerSecond: 4 } },
    })
    clientSignature = signature
  }
  return client
}

export function resetSupabaseClient() {
  const previousClient = client
  client = null
  clientSignature = ''
  if (!previousClient) return Promise.resolve()

  return Promise.allSettled([
    previousClient.removeAllChannels(),
    previousClient.auth.dispose(),
  ]).then(() => undefined)
}

export function buildAuthCallbackUrl(baseUrl, flow) {
  const normalizedFlow = flow === 'recovery' ? 'recovery' : 'confirmation'
  const value = String(baseUrl || '').trim()
  if (!value) throw new Error('Auth callback URL oluşturulamadı.')

  if (value.includes('{flow}')) {
    return value.replace('{flow}', encodeURIComponent(normalizedFlow))
  }

  if (value.includes('#/auth/callback')) {
    const separator = value.includes('?') ? '&' : '?'
    return `${value}${separator}flow=${encodeURIComponent(normalizedFlow)}`
  }

  const parsed = new URL(value)
  parsed.searchParams.set('flow', normalizedFlow)
  return parsed.toString()
}

export function getAuthCallbackUrl(flow) {
  const configured = import.meta.env?.QCLI_AUTH_REDIRECT_URL?.trim() || ''
  if (configured) return buildAuthCallbackUrl(configured, flow)

  if (typeof window === 'undefined')
    throw new Error('Auth callback URL yalnız istemcide üretilebilir.')
  if (window.location.protocol === 'capacitor:') {
    throw new Error('Capacitor için QCLI_AUTH_REDIRECT_URL deep-link adresi yapılandırılmalı.')
  }

  const base = `${window.location.origin}${window.location.pathname}#/auth/callback`
  return buildAuthCallbackUrl(base, flow)
}

async function readErrorResponse(response) {
  try {
    const payload = await response.json()
    return payload?.msg || payload?.message || payload?.error || response.statusText
  } catch {
    return response.statusText
  }
}

export async function testSupabaseConnection(config, { timeoutMs = 10000 } = {}) {
  const normalized = normalizeSupabaseConnection(config)
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  const startedAt = performance.now()

  try {
    const response = await fetch(`${normalized.url}/auth/v1/health`, {
      method: 'GET',
      headers: {
        apikey: normalized.publishableKey,
        Authorization: `Bearer ${normalized.publishableKey}`,
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      const error = new Error((await readErrorResponse(response)) || 'Supabase Auth erişilemedi.')
      error.status = response.status
      throw error
    }

    return {
      status: 'ok',
      authApi: 'ok',
      authenticatedRls: 'not_tested',
      latencyMs: Math.round(performance.now() - startedAt),
      checkedAt: new Date().toISOString(),
      message: 'Supabase Auth servisine bağlantı başarılı.',
    }
  } catch (error) {
    throw asSupabaseAppError(error, 'Supabase bağlantı testi başarısız.')
  } finally {
    clearTimeout(timeout)
  }
}

export async function testAuthenticatedSupabaseAccess(activeClient, expectedUserId) {
  if (!activeClient || !expectedUserId) throw new Error('RLS testi için aktif oturum gerekli.')

  const startedAt = performance.now()
  try {
    const { data: userData, error: userError } = await activeClient.auth.getUser()
    if (userError) throw userError
    if (userData.user?.id !== expectedUserId) {
      const error = new Error('Supabase Auth kullanıcısı ile yerel oturum eşleşmiyor.')
      error.code = 'session_not_found'
      throw error
    }

    const [profileResult, accountResult, marketResult] = await Promise.all([
      activeClient.from('profiles').select('user_id').eq('user_id', expectedUserId).limit(1),
      activeClient
        .from('investment_accounts')
        .select('id,user_id')
        .eq('user_id', expectedUserId)
        .limit(1),
      activeClient.from('market_snapshot').select('symbol').limit(1),
    ])

    for (const result of [profileResult, accountResult, marketResult]) {
      if (result.error) throw result.error
    }

    return {
      status: 'ok',
      authApi: 'ok',
      authenticatedRls: 'ok',
      latencyMs: Math.round(performance.now() - startedAt),
      checkedAt: new Date().toISOString(),
      message: 'Auth oturumu ve kullanıcıya ait RLS erişimi doğrulandı.',
    }
  } catch (error) {
    throw asSupabaseAppError(error, 'Auth/RLS bağlantı testi başarısız.')
  }
}

function callbackParameters(callbackUrl) {
  const parsed = new URL(callbackUrl)
  const parameters = new URLSearchParams(parsed.search)
  const hash = parsed.hash.replace(/^#/, '')
  const hashQuery = hash.includes('?') ? hash.slice(hash.indexOf('?') + 1) : hash
  for (const [key, value] of new URLSearchParams(hashQuery)) {
    if (!parameters.has(key)) parameters.set(key, value)
  }
  return parameters
}

export async function consumeAuthCallbackUrl(callbackUrl) {
  const activeClient = getSupabaseClient()
  if (!activeClient) throw new Error('Supabase bağlantısı yapılandırılmamış.')

  const parameters = callbackParameters(callbackUrl)
  const code = parameters.get('code')
  const accessToken = parameters.get('access_token')
  const refreshToken = parameters.get('refresh_token')

  try {
    if (code) {
      const { error } = await activeClient.auth.exchangeCodeForSession(code)
      if (error) throw error
    } else if (accessToken && refreshToken) {
      const { error } = await activeClient.auth.setSession({
        access_token: accessToken,
        refresh_token: refreshToken,
      })
      if (error) throw error
    }

    return {
      flow: parameters.get('flow') || parameters.get('type') || 'confirmation',
      handled: Boolean(code || (accessToken && refreshToken)),
    }
  } catch (error) {
    throw asSupabaseAppError(error, 'Auth dönüş bağlantısı işlenemedi.')
  }
}
