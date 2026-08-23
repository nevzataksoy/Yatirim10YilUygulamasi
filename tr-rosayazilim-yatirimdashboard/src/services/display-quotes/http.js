import { Capacitor, CapacitorHttp } from '@capacitor/core'

const DEFAULT_TIMEOUT_MS = 10_000

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
    const response = await CapacitorHttp.get({
      url,
      params: normalizedParams,
      headers,
      connectTimeout: timeout,
      readTimeout: timeout,
    })

    if (response.status < 200 || response.status >= 300) {
      throw new Error(`HTTP ${response.status}: ${url}`)
    }
    return response.data
  }

  const target = new URL(url)
  Object.entries(normalizedParams).forEach(([key, value]) => target.searchParams.set(key, value))
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(target, { headers, signal: controller.signal })
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`)
    return await response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}
