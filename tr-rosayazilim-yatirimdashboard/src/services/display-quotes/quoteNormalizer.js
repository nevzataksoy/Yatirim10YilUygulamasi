import { DISPLAY_QUOTE_KEYS } from './quoteConfig.js'

export function toPositiveNumber(value, label = 'quote') {
  const number = Number(value)
  if (!Number.isFinite(number) || number <= 0) {
    throw new Error(`${label} geçerli pozitif bir sayı değil.`)
  }
  return number
}

function normalizeDate(value, fallback = null) {
  if (!value) return fallback
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? fallback : date.toISOString()
}

export function normalizeQuote({
  key,
  value,
  provider,
  providerType = 'public',
  quality = 'current',
  marketAt = null,
  fetchedAt = new Date().toISOString(),
  fallbackLevel = 0,
  upstreamProvider = null,
}) {
  if (!DISPLAY_QUOTE_KEYS.includes(key)) {
    throw new Error(`Desteklenmeyen display quote anahtarı: ${key}`)
  }

  const normalizedFetchedAt = normalizeDate(fetchedAt, new Date().toISOString())

  return {
    key,
    value: toPositiveNumber(value, key),
    provider: String(provider || 'unknown'),
    providerType: String(providerType || 'public'),
    quality: String(quality || 'current'),
    marketAt: normalizeDate(marketAt, marketAt || null),
    fetchedAt: normalizedFetchedAt,
    fallbackLevel: Number.isFinite(Number(fallbackLevel)) ? Number(fallbackLevel) : 0,
    upstreamProvider: upstreamProvider ? String(upstreamProvider) : null,
  }
}

export function isDisplayQuote(value) {
  return Boolean(
    value &&
    DISPLAY_QUOTE_KEYS.includes(value.key) &&
    Number.isFinite(Number(value.value)) &&
    Number(value.value) > 0,
  )
}
