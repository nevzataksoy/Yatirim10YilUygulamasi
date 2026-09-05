import { getJson } from '../http.js'
import { normalizeQuote } from '../quoteNormalizer.js'
import { parseCoinbaseSpot, parseCoinbaseUsdFx } from '../quoteParsers.js'

const COINBASE_API = 'https://api.coinbase.com/v2'

export async function fetchCoinbaseSpotQuote(asset) {
  const symbol = String(asset || '').toUpperCase()
  if (symbol !== 'BTC' && symbol !== 'ETH')
    throw new Error(`Desteklenmeyen Coinbase varlığı: ${symbol}`)

  const data = await getJson(`${COINBASE_API}/prices/${symbol}-USD/spot`)
  const fetchedAt = new Date().toISOString()

  return normalizeQuote({
    key: `${symbol}_USD`,
    value: parseCoinbaseSpot(data),
    provider: 'coinbase-spot',
    providerType: 'official',
    quality: 'live',
    fetchedAt,
  })
}

export async function fetchCoinbaseFxQuotes() {
  const data = await getJson(`${COINBASE_API}/exchange-rates`, { params: { currency: 'USD' } })
  const values = parseCoinbaseUsdFx(data)
  const fetchedAt = new Date().toISOString()

  return Object.entries(values).map(([key, value]) =>
    normalizeQuote({
      key,
      value,
      provider: 'coinbase-exchange-rates',
      providerType: 'official',
      quality: 'current',
      fetchedAt,
    }),
  )
}
