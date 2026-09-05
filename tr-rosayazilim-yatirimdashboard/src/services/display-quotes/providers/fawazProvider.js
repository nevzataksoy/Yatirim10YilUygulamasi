import { getJson } from '../http.js'
import { normalizeQuote } from '../quoteNormalizer.js'
import { parseFawazUsdFx } from '../quoteParsers.js'

const FAWAZ_ENDPOINTS = [
  'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.min.json',
  'https://latest.currency-api.pages.dev/v1/currencies/usd.json',
]

async function fetchFawazData() {
  let lastError = null
  for (const url of FAWAZ_ENDPOINTS) {
    try {
      return await getJson(url)
    } catch (error) {
      lastError = error
    }
  }
  throw lastError instanceof Error ? lastError : new Error('Fawaz Currency API verisi alınamadı.')
}

export async function fetchFawazFxQuotes() {
  const data = await fetchFawazData()
  const values = parseFawazUsdFx(data)
  const fetchedAt = new Date().toISOString()

  return Object.entries(values).map(([key, item]) =>
    normalizeQuote({
      key,
      value: item.value,
      provider: 'fawaz-currency-api',
      providerType: 'open-source',
      quality: 'daily',
      marketAt: item.marketAt,
      fetchedAt,
    }),
  )
}
