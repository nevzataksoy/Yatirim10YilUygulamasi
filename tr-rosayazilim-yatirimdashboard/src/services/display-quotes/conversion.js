function quoteValue(quotes, key) {
  const raw = quotes?.[key]
  const value = Number(raw?.value ?? raw ?? 0)
  return Number.isFinite(value) && value > 0 ? value : 0
}

export function priceUsdForAsset(quotes, asset) {
  if (asset === 'USD') return 1
  if (asset === 'TRY') {
    const usdTry = quoteValue(quotes, 'USD_TRY')
    return usdTry > 0 ? 1 / usdTry : 0
  }
  if (asset === 'EUR') return quoteValue(quotes, 'EUR_USD')
  if (asset === 'BTC') return quoteValue(quotes, 'BTC_USD')
  if (asset === 'ETH') return quoteValue(quotes, 'ETH_USD')
  if (asset === 'URA') return quoteValue(quotes, 'URA_USD')
  return 0
}

export function convertUsdWithQuotes(value, asset, quotes) {
  const usd = Number(value || 0)
  if (!Number.isFinite(usd)) return 0
  if (asset === 'USD') return usd

  if (asset === 'TRY') {
    const usdTry = quoteValue(quotes, 'USD_TRY')
    return usdTry > 0 ? usd * usdTry : 0
  }

  const assetPriceUsd = priceUsdForAsset(quotes, asset)
  return assetPriceUsd > 0 ? usd / assetPriceUsd : 0
}
