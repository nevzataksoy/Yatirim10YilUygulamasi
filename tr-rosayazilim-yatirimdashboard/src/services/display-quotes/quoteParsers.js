import { toPositiveNumber } from './quoteNormalizer.js'

function optionalPositiveNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : null
}

function requireAtLeastOne(result, label) {
  if (!Object.keys(result).length) throw new Error(`${label} kullanılabilir kur döndürmedi.`)
  return result
}

export function parseCoinbaseSpot(data) {
  return toPositiveNumber(data?.data?.amount, 'Coinbase spot')
}

export function parseCoinbaseUsdFx(data) {
  const rates = data?.data?.rates || {}
  const result = {}
  const usdTry = optionalPositiveNumber(rates.TRY)
  const usdEur = optionalPositiveNumber(rates.EUR)

  if (usdTry) result.USD_TRY = usdTry
  if (usdEur) result.EUR_USD = 1 / usdEur
  return requireAtLeastOne(result, 'Coinbase')
}

export function parseYahooChart(data) {
  const meta = data?.chart?.result?.[0]?.meta
  const value = toPositiveNumber(meta?.regularMarketPrice, 'Yahoo quote')
  const marketAt = Number(meta?.regularMarketTime)

  return {
    value,
    marketAt:
      Number.isFinite(marketAt) && marketAt > 0 ? new Date(marketAt * 1000).toISOString() : null,
  }
}

export function parseFrankfurterUsdFx(data) {
  const result = {}

  if (Array.isArray(data)) {
    const byQuote = Object.fromEntries(
      data.map((item) => [String(item?.quote || '').toUpperCase(), item]),
    )
    const tryItem = byQuote.TRY
    const eurItem = byQuote.EUR
    const usdTry = optionalPositiveNumber(tryItem?.rate)
    const usdEur = optionalPositiveNumber(eurItem?.rate)

    if (usdTry) result.USD_TRY = { value: usdTry, marketAt: tryItem?.date || null }
    if (usdEur) result.EUR_USD = { value: 1 / usdEur, marketAt: eurItem?.date || null }
    return requireAtLeastOne(result, 'Frankfurter')
  }

  const rates = data?.rates || {}
  const usdTry = optionalPositiveNumber(rates.TRY)
  const usdEur = optionalPositiveNumber(rates.EUR)

  if (usdTry) result.USD_TRY = { value: usdTry, marketAt: data?.date || null }
  if (usdEur) result.EUR_USD = { value: 1 / usdEur, marketAt: data?.date || null }
  return requireAtLeastOne(result, 'Frankfurter')
}

export function parseFawazUsdFx(data) {
  const rates = data?.usd || {}
  const result = {}
  const usdTry = optionalPositiveNumber(rates.try)
  const usdEur = optionalPositiveNumber(rates.eur)

  if (usdTry) result.USD_TRY = { value: usdTry, marketAt: data?.date || null }
  if (usdEur) result.EUR_USD = { value: 1 / usdEur, marketAt: data?.date || null }
  return requireAtLeastOne(result, 'Fawaz Currency API')
}
