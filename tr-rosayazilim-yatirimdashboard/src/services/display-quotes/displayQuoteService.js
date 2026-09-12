import { DISPLAY_QUOTE_FALLBACK_LEVEL } from './quoteConfig.js'
import { fetchCoinbaseFxQuotes, fetchCoinbaseSpotQuote } from './providers/coinbaseProvider.js'
import { fetchFawazFxQuotes } from './providers/fawazProvider.js'
import { fetchFrankfurterFxQuotes } from './providers/frankfurterProvider.js'
import { fetchYahooFxQuotes, fetchYahooUraQuote } from './providers/yahooProvider.js'

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error || 'Bilinmeyen provider hatası')
}

function withFallbackLevel(quote, fallbackLevel) {
  return { ...quote, fallbackLevel }
}

export async function fetchCryptoDisplayQuotes() {
  const assets = ['BTC', 'ETH', 'USDT', 'USDC']
  const results = await Promise.allSettled(assets.map((asset) => fetchCoinbaseSpotQuote(asset)))
  const quotes = []
  const errors = {}
  const missingStablecoins = []

  results.forEach((result, index) => {
    const asset = assets[index]
    const key = `${asset}_USD`
    if (result.status === 'fulfilled') {
      quotes.push(withFallbackLevel(result.value, DISPLAY_QUOTE_FALLBACK_LEVEL.PRIMARY))
    } else {
      errors[`coinbase:${key}`] = errorMessage(result.reason)
      if (asset === 'USDT' || asset === 'USDC') missingStablecoins.push(key)
      else errors[key] = errorMessage(result.reason)
    }
  })

  if (missingStablecoins.length) {
    try {
      const yahooQuotes = await fetchYahooFxQuotes(missingStablecoins)
      const recovered = new Set()
      for (const quote of yahooQuotes) {
        if (!missingStablecoins.includes(quote.key)) continue
        quotes.push(withFallbackLevel(quote, DISPLAY_QUOTE_FALLBACK_LEVEL.PROVIDER_FALLBACK))
        recovered.add(quote.key)
      }
      for (const key of missingStablecoins) {
        if (!recovered.has(key)) errors[key] = 'Coinbase Spot ve Yahoo stablecoin fiyatı alınamadı.'
      }
    } catch (error) {
      for (const key of missingStablecoins) {
        errors[key] = `Coinbase Spot ve Yahoo stablecoin fiyatı alınamadı: ${errorMessage(error)}`
      }
    }
  }

  return { quotes, errors }
}

export async function fetchFxDisplayQuotes() {
  const missing = new Set(['USD_TRY', 'EUR_USD'])
  const quotes = []
  const errors = {}
  const providers = [
    {
      name: 'coinbase',
      level: DISPLAY_QUOTE_FALLBACK_LEVEL.PRIMARY,
      fetcher: () => fetchCoinbaseFxQuotes(),
    },
    {
      name: 'yahoo',
      level: DISPLAY_QUOTE_FALLBACK_LEVEL.PROVIDER_FALLBACK,
      fetcher: () => fetchYahooFxQuotes([...missing]),
    },
    {
      name: 'frankfurter',
      level: DISPLAY_QUOTE_FALLBACK_LEVEL.DAILY_FALLBACK,
      fetcher: () => fetchFrankfurterFxQuotes(),
    },
    {
      name: 'fawaz',
      level: DISPLAY_QUOTE_FALLBACK_LEVEL.SECONDARY_DAILY_FALLBACK,
      fetcher: () => fetchFawazFxQuotes(),
    },
  ]

  for (const provider of providers) {
    if (!missing.size) break
    try {
      const providerQuotes = await provider.fetcher()
      for (const quote of providerQuotes) {
        if (!missing.has(quote.key)) continue
        quotes.push(withFallbackLevel(quote, provider.level))
        missing.delete(quote.key)
      }
    } catch (error) {
      errors[provider.name] = errorMessage(error)
    }
  }

  for (const key of missing) {
    errors[key] = errors[key] || 'Tüm keyless FX provider zinciri başarısız oldu.'
  }

  return { quotes, errors }
}

export async function fetchUraDisplayQuote() {
  try {
    return {
      quotes: [withFallbackLevel(await fetchYahooUraQuote(), DISPLAY_QUOTE_FALLBACK_LEVEL.PRIMARY)],
      errors: {},
    }
  } catch (error) {
    return { quotes: [], errors: { URA_USD: errorMessage(error) } }
  }
}

export async function fetchSlowDisplayQuotes() {
  const [fxResult, uraResult] = await Promise.allSettled([
    fetchFxDisplayQuotes(),
    fetchUraDisplayQuote(),
  ])
  const quotes = []
  const errors = {}

  if (fxResult.status === 'fulfilled') {
    quotes.push(...fxResult.value.quotes)
    Object.assign(errors, fxResult.value.errors)
  } else {
    errors.fx = errorMessage(fxResult.reason)
  }

  if (uraResult.status === 'fulfilled') {
    quotes.push(...uraResult.value.quotes)
    Object.assign(errors, uraResult.value.errors)
  } else {
    errors.URA_USD = errorMessage(uraResult.reason)
  }

  return { quotes, errors }
}
