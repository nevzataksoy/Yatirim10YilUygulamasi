import { isStablecoin, stablecoinRateFromTransaction } from './transactionCurrency.js'

export const EXACT_HISTORICAL_DISPLAY_ASSETS = Object.freeze(['USD', 'TRY', 'USDT', 'USDC'])

export function historicalUsdUnitPrice(transaction, asset) {
  const symbol = String(asset || '').toUpperCase()
  if (symbol === 'USD') return 1

  if (symbol === 'TRY') {
    const usdTry = Number(transaction?.usd_try || 0)
    return Number.isFinite(usdTry) && usdTry > 0 ? 1 / usdTry : 0
  }

  if (isStablecoin(symbol)) {
    return stablecoinRateFromTransaction(transaction, symbol)
  }

  return 0
}

export function historicalUsdToAsset(transaction, usdValue, asset) {
  const usd = Number(usdValue || 0)
  if (!Number.isFinite(usd)) return null
  if (usd === 0) return 0

  const unitUsd = historicalUsdUnitPrice(transaction, asset)
  return unitUsd > 0 ? usd / unitUsd : null
}

export function historicalAggregate(rows, valueSelector, asset) {
  let total = 0
  for (const row of rows || []) {
    const converted = historicalUsdToAsset(row, valueSelector(row), asset)
    if (converted === null) return null
    total += converted
  }
  return total
}
