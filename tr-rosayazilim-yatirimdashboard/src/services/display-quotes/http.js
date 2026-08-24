import { Notify } from 'quasar'
import { Capacitor, CapacitorHttp } from '@capacitor/core'

const DEFAULT_TIMEOUT_MS = 10_000
const ERROR_NOTIFY_COOLDOWN_MS = 60_000

const WEB_DEV_PROXY_TARGETS = Object.freeze({
  'https://query1.finance.yahoo.com': '/__display-quotes/yahoo',
})

const lastErrorNotifyAt = new Map()

function providerNameFromUrl(url) {
  if (url.includes('query1.finance.yahoo.com')) return 'Yahoo Finance'
  if (url.includes('api.coinbase.com')) return 'Coinbase'
  if (url.includes('frankfurter.dev')) return 'Frankfurter'
  if (
    url.includes('currency-api.pages.dev') ||
    url.includes('cdn.jsdelivr.net')
  ) {
    return 'Fawaz Currency API'
  }

  return 'Display Quote Provider'
}

function sanitizeErrorDetail(detail) {
  return String(detail || '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 180)
}

function notifyHttpError({
  url,
  status = null,
  detail = '',
}) {
  const provider = providerNameFromUrl(url)
  const key = `${provider}:${status || 'network'}`

  const now = Date.now()
  const lastShownAt = lastErrorNotifyAt.get(key) || 0

  if (now - lastShownAt < ERROR_NOTIFY_COOLDOWN_MS) {
    return
  }

  lastErrorNotifyAt.set(key, now)

  const statusText = status
    ? `HTTP ${status}`
    : 'Bağlantı hatası'

  const safeDetail = sanitizeErrorDetail(detail)

  Notify.create({
    type: 'negative',
    icon: 'cloud_off',
    position: 'top',
    timeout: 6000,
    message: `${provider} fiyat isteği başarısız`,
    caption: safeDetail
      ? `${statusText} · ${safeDetail}`
      : `${statusText} · Alternatif fiyat kaynağı deneniyor.`,
  })
}

function buildNativeHeaders(headers = {}) {
  const nativeHeaders = { ...headers }

  const hasUserAgent =
    nativeHeaders['User-Agent'] ||
    nativeHeaders['user-agent']

  if (
    !hasUserAgent &&
    typeof navigator !== 'undefined' &&
    navigator.userAgent
  ) {
    nativeHeaders['User-Agent'] = navigator.userAgent
  }

  return nativeHeaders
}

function resolveWebRequestUrl(url) {
  if (!import.meta.env.DEV) return url

  for (const [origin, proxyPrefix] of Object.entries(WEB_DEV_PROXY_TARGETS)) {
    if (url.startsWith(origin)) {
      return `${proxyPrefix}${url.slice(origin.length)}`
    }
  }

  return url
}

function normalizeParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).map(([key, value]) => [
      key,
      value === undefined ? '' : String(value),
    ]),
  )
}

export async function getJson(
  url,
  { params = {}, headers = {}, timeout = DEFAULT_TIMEOUT_MS } = {},
) {
  const normalizedParams = normalizeParams(params)

  if (Capacitor.isNativePlatform()) {
    try {
      const response = await CapacitorHttp.get({
        url,
        params: normalizedParams,
        headers: buildNativeHeaders(headers),
        connectTimeout: timeout,
        readTimeout: timeout,
      })

      if (response.status < 200 || response.status >= 300) {
        const responseDetail =
          typeof response.data === 'string'
            ? response.data
            : JSON.stringify(response.data || {})

        notifyHttpError({
          url,
          status: response.status,
          detail: responseDetail,
        })

        throw new Error(
          `HTTP ${response.status}: ${url} - ${responseDetail.slice(0, 300)}`,
        )
      }

      return response.data
    } catch (error) {
      /*
      * Yukarıdaki HTTP status hatasında notify zaten gösterildi.
      * Burada yalnız gerçek network/native exception'larında
      * ayrıca bildirim gösteriyoruz.
      */
      if (
        !String(error?.message || '').startsWith('HTTP ')
      ) {
        notifyHttpError({
          url,
          detail:
            error instanceof Error
              ? error.message
              : String(error || 'Bilinmeyen bağlantı hatası'),
        })
      }

      throw error
    }
  }

  const webUrl = resolveWebRequestUrl(url)
  const target = new URL(webUrl, window.location.origin)

  Object.entries(normalizedParams).forEach(([key, value]) =>
    target.searchParams.set(key, value),
  )
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(target, {
      headers,
      signal: controller.signal,
    })

    if (!response.ok) {
      const responseDetail = await response
        .text()
        .catch(() => '')

      notifyHttpError({
        url,
        status: response.status,
        detail: responseDetail,
      })

      throw new Error(
        `HTTP ${response.status}: ${url}`,
      )
    }

    return await response.json()
  } catch (error) {
    if (
      !String(error?.message || '').startsWith('HTTP ')
    ) {
      notifyHttpError({
        url,
        detail:
          error instanceof Error
            ? error.message
            : String(error || 'Bilinmeyen bağlantı hatası'),
      })
    }

    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}
