import { DISPLAY_QUOTE_FALLBACK_LEVEL } from '../quoteConfig.js'
import { normalizeQuote } from '../quoteNormalizer.js'

const SNAPSHOT_SYMBOLS = Object.freeze({
  'BTC/USD': 'BTC_USD',
  'ETH/USD': 'ETH_USD',
  'URA/USD': 'URA_USD',
  'USD/TRY': 'USD_TRY',
})

export function quotesFromMarketSnapshot(market = [], keys = null) {
  const wanted = keys ? new Set(keys) : null
  const fetchedAt = new Date().toISOString()
  const quotes = []

  for (const item of market || []) {
    const key = SNAPSHOT_SYMBOLS[item?.symbol]
    if (!key || (wanted && !wanted.has(key))) continue

    try {
      quotes.push(
        normalizeQuote({
          key,
          value: item.value,
          provider: 'market-snapshot',
          providerType: 'engine-fallback',
          quality: 'snapshot',
          marketAt: item.data_date || item.as_of || item.generated_at || null,
          fetchedAt,
          fallbackLevel: DISPLAY_QUOTE_FALLBACK_LEVEL.MARKET_SNAPSHOT,
          upstreamProvider: item.provider || null,
        }),
      )
    } catch {
      // A malformed snapshot row is ignored; other pairs must still remain usable.
    }
  }

  return quotes
}
