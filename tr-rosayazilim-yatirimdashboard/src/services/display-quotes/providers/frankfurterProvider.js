import { getJson } from '../http.js'
import { normalizeQuote } from '../quoteNormalizer.js'
import { parseFrankfurterUsdFx } from '../quoteParsers.js'

const FRANKFURTER_API = 'https://api.frankfurter.dev/v2/rates'

export async function fetchFrankfurterFxQuotes() {
  const data = await getJson(FRANKFURTER_API, {
    params: { base: 'USD', quotes: 'TRY,EUR', providers: 'TCMB' },
  })
  const values = parseFrankfurterUsdFx(data)
  const fetchedAt = new Date().toISOString()

  return Object.entries(values).map(([key, item]) =>
    normalizeQuote({
      key,
      value: item.value,
      provider: 'frankfurter-central-banks',
      providerType: 'official-source',
      quality: 'daily',
      marketAt: item.marketAt,
      fetchedAt,
    }),
  )
}
