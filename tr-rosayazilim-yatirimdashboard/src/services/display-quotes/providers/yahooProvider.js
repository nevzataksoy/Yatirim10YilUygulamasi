import { getJson } from '../http.js'
import { normalizeQuote } from '../quoteNormalizer.js'
import { parseYahooChart } from '../quoteParsers.js'

const YAHOO_CHART_API = 'https://query1.finance.yahoo.com/v8/finance/chart'
const FX_SYMBOLS = Object.freeze({
  USD_TRY: 'TRY=X',
  EUR_USD: 'EURUSD=X',
})

async function fetchYahooChartQuote({ key, symbol, quality }) {
  const data = await getJson(`${YAHOO_CHART_API}/${encodeURIComponent(symbol)}`, {
    params: { interval: '1m', range: '1d' },
    headers: { Accept: 'application/json' },
  })
  const parsed = parseYahooChart(data)

  return normalizeQuote({
    key,
    value: parsed.value,
    provider: 'yahoo-finance',
    providerType: 'unofficial',
    quality,
    marketAt: parsed.marketAt,
    fetchedAt: new Date().toISOString(),
  })
}

export function fetchYahooUraQuote() {
  return fetchYahooChartQuote({ key: 'URA_USD', symbol: 'URA', quality: 'delayed' })
}

export async function fetchYahooFxQuotes(keys = Object.keys(FX_SYMBOLS)) {
  const requested = keys.filter((key) => FX_SYMBOLS[key])
  const results = await Promise.allSettled(
    requested.map((key) =>
      fetchYahooChartQuote({ key, symbol: FX_SYMBOLS[key], quality: 'current' }),
    ),
  )
  const quotes = results
    .filter((result) => result.status === 'fulfilled')
    .map((result) => result.value)

  if (!quotes.length && requested.length) {
    const firstError = results.find((result) => result.status === 'rejected')?.reason
    throw firstError instanceof Error ? firstError : new Error('Yahoo Finance FX verisi alınamadı.')
  }

  return quotes
}
