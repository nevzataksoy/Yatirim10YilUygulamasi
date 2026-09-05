import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { convertUsdWithQuotes, priceUsdForAsset } from '@/services/display-quotes/conversion'
import {
  DISPLAY_QUOTE_CACHE_KEY,
  DISPLAY_QUOTE_CACHE_WRITE_MS,
  DISPLAY_QUOTE_FALLBACK_LEVEL,
  DISPLAY_QUOTE_KEYS,
  DISPLAY_QUOTE_STALE_MS,
} from '@/services/display-quotes/quoteConfig'
import { isDisplayQuote, normalizeQuote } from '@/services/display-quotes/quoteNormalizer'
import { quotesFromMarketSnapshot } from '@/services/display-quotes/providers/snapshotProvider'
import { getSecureValue, setSecureValue } from '@/services/secureStorage'

function emptyQuoteMap() {
  return Object.fromEntries(DISPLAY_QUOTE_KEYS.map((key) => [key, null]))
}

function timestamp(value) {
  const time = value ? new Date(value).getTime() : 0
  return Number.isFinite(time) ? time : 0
}

export const useDisplayQuoteStore = defineStore('displayQuotes', () => {
  const quotes = ref(emptyQuoteMap())
  const lastRefreshAt = ref(null)
  const lastError = ref('')
  const providerErrors = ref({})
  const hydrated = ref(false)
  let lastPersistAt = 0

  const ready = computed(() => DISPLAY_QUOTE_KEYS.every((key) => isDisplayQuote(quotes.value[key])))

  function isStale(key, quote = quotes.value[key], now = Date.now()) {
    if (!isDisplayQuote(quote)) return true
    const maxAge = DISPLAY_QUOTE_STALE_MS[key] || 5 * 60_000
    return now - timestamp(quote.fetchedAt) > maxAge
  }

  function shouldReplace(current, incoming, allowWorseWhenStale = false) {
    if (!isDisplayQuote(current)) return true
    if (incoming.fallbackLevel < current.fallbackLevel) return true
    if (incoming.fallbackLevel > current.fallbackLevel) {
      return allowWorseWhenStale && isStale(incoming.key, current)
    }
    return timestamp(incoming.fetchedAt) >= timestamp(current.fetchedAt)
  }

  function applyQuote(incoming, { allowWorseWhenStale = false } = {}) {
    if (!isDisplayQuote(incoming)) return false
    const current = quotes.value[incoming.key]
    if (!shouldReplace(current, incoming, allowWorseWhenStale)) return false
    quotes.value[incoming.key] = { ...incoming }
    return true
  }

  function applyQuotes(items, options = {}) {
    let changed = false
    for (const item of items || []) changed = applyQuote(item, options) || changed
    if (changed) lastRefreshAt.value = new Date().toISOString()
    return changed
  }

  function applySnapshotFallback(market, keys = null) {
    return applyQuotes(quotesFromMarketSnapshot(market, keys), { allowWorseWhenStale: true })
  }

  function setProviderErrors(group, errors = {}) {
    providerErrors.value = { ...providerErrors.value, [group]: { ...errors } }
    lastError.value = Object.values(providerErrors.value)
      .flatMap((item) => Object.values(item || {}))
      .filter(Boolean)
      .join(' | ')
  }

  function hydrateCache() {
    if (hydrated.value) return
    hydrated.value = true
    const cached = getSecureValue(DISPLAY_QUOTE_CACHE_KEY, null)
    const cachedQuotes = cached?.quotes || cached
    if (!cachedQuotes || typeof cachedQuotes !== 'object') return

    for (const key of DISPLAY_QUOTE_KEYS) {
      const item = cachedQuotes[key]
      if (!isDisplayQuote(item)) continue
      try {
        applyQuote(
          normalizeQuote({
            ...item,
            key,
            provider: 'device-cache',
            providerType: 'device-cache',
            quality: 'cached',
            fallbackLevel: DISPLAY_QUOTE_FALLBACK_LEVEL.DEVICE_CACHE,
            upstreamProvider: item.provider || item.upstreamProvider || null,
          }),
        )
      } catch {
        // Ignore corrupt or obsolete cache entries pair-by-pair.
      }
    }
  }

  function persistCache(force = false) {
    const now = Date.now()
    if (!force && now - lastPersistAt < DISPLAY_QUOTE_CACHE_WRITE_MS) return false

    const serializable = Object.fromEntries(
      DISPLAY_QUOTE_KEYS.filter((key) => isDisplayQuote(quotes.value[key])).map((key) => [
        key,
        { ...quotes.value[key] },
      ]),
    )
    if (!Object.keys(serializable).length) return false

    const written = setSecureValue(DISPLAY_QUOTE_CACHE_KEY, {
      version: 1,
      savedAt: new Date(now).toISOString(),
      quotes: serializable,
    })
    if (written) lastPersistAt = now
    return written
  }

  function priceUsd(asset) {
    return priceUsdForAsset(quotes.value, asset)
  }

  function convertUsd(value, asset) {
    return convertUsdWithQuotes(value, asset, quotes.value)
  }

  return {
    quotes,
    lastRefreshAt,
    lastError,
    providerErrors,
    hydrated,
    ready,
    hydrateCache,
    persistCache,
    applyQuote,
    applyQuotes,
    applySnapshotFallback,
    setProviderErrors,
    isStale,
    priceUsd,
    convertUsd,
  }
})
