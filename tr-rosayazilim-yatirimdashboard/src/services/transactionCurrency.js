export const STABLECOIN_ASSETS = Object.freeze(['USDT', 'USDC'])
export const SETTLEMENT_ASSET_OPTIONS = Object.freeze(['TRY', 'USD', ...STABLECOIN_ASSETS])

export function isStablecoin(asset) {
  return STABLECOIN_ASSETS.includes(String(asset || '').toUpperCase())
}

export function stablecoinQuoteKey(asset) {
  const symbol = String(asset || '').toUpperCase()
  return isStablecoin(symbol) ? `${symbol}_USD` : null
}

export function actualStablecoinUsdQuote(quotes, asset) {
  const key = stablecoinQuoteKey(asset)
  if (!key) return 0
  const value = Number(quotes?.[key]?.value || 0)
  return Number.isFinite(value) && value > 0 ? value : 0
}

export function settlementUsdUnitPrice(asset, { usdTry = 0, stablecoinUsd = 0 } = {}) {
  const symbol = String(asset || '').toUpperCase()
  if (symbol === 'USD') return 1
  if (symbol === 'TRY') {
    const fx = Number(usdTry || 0)
    return Number.isFinite(fx) && fx > 0 ? 1 / fx : 0
  }
  if (isStablecoin(symbol)) {
    const rate = Number(stablecoinUsd || 0)
    return Number.isFinite(rate) && rate > 0 ? rate : 0
  }
  return 0
}

export function settlementAmountToUsd(value, asset, rates = {}) {
  const amount = Number(value || 0)
  const unitUsd = settlementUsdUnitPrice(asset, rates)
  return Number.isFinite(amount) && unitUsd > 0 ? amount * unitUsd : 0
}

export function stablecoinRatesMetadata(entries = []) {
  const rates = {}
  for (const [asset, value] of entries) {
    if (!isStablecoin(asset)) continue
    const rate = Number(value || 0)
    if (Number.isFinite(rate) && rate > 0) rates[String(asset).toUpperCase()] = rate
  }
  return Object.keys(rates).length ? { stablecoin_usd_rates: rates } : {}
}

export function stablecoinRateFromMetadata(metadata, asset) {
  if (!isStablecoin(asset)) return 0
  const value = Number(metadata?.stablecoin_usd_rates?.[String(asset).toUpperCase()] || 0)
  return Number.isFinite(value) && value > 0 ? value : 0
}

export function formatSettlementAmount(value, asset, maximumFractionDigits = 2) {
  const symbol = String(asset || '').toUpperCase()
  const amount = Number(value || 0)
  if (symbol === 'USD' || symbol === 'TRY') {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: symbol,
      maximumFractionDigits,
    }).format(amount)
  }
  return `${new Intl.NumberFormat('tr-TR', {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(amount)} ${symbol}`
}
