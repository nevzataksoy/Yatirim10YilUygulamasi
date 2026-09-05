export const DISPLAY_QUOTE_KEYS = Object.freeze([
  'BTC_USD',
  'ETH_USD',
  'URA_USD',
  'USD_TRY',
  'EUR_USD',
])

export const DISPLAY_QUOTE_FALLBACK_LEVEL = Object.freeze({
  PRIMARY: 0,
  PROVIDER_FALLBACK: 10,
  DAILY_FALLBACK: 20,
  SECONDARY_DAILY_FALLBACK: 30,
  MARKET_SNAPSHOT: 50,
  DEVICE_CACHE: 90,
})

export const DISPLAY_QUOTE_REFRESH_MS = Object.freeze({
  crypto: 30_000,
  slow: 60_000,
})

export const DISPLAY_QUOTE_STALE_MS = Object.freeze({
  BTC_USD: 2 * 60_000,
  ETH_USD: 2 * 60_000,
  URA_USD: 5 * 60_000,
  USD_TRY: 5 * 60_000,
  EUR_USD: 5 * 60_000,
})

export const DISPLAY_QUOTE_BACKOFF_MS = Object.freeze([60_000, 120_000, 300_000, 900_000])
export const DISPLAY_QUOTE_CACHE_KEY = 'market:display-quotes:v1'
export const DISPLAY_QUOTE_CACHE_WRITE_MS = 5 * 60_000
