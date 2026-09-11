const QUANTITY_DIGITS = Object.freeze({
  BTC: 8,
  ETH: 6,
  URA: 4,
  USDT: 6,
  USDC: 6,
  USD: 2,
  TRY: 2,
})

export function assetQuantityDigits(asset) {
  return QUANTITY_DIGITS[String(asset || '').toUpperCase()] ?? 8
}

export function formatAssetQuantity(value, asset, locale = 'tr-TR') {
  const symbol = String(asset || '').toUpperCase()
  const amount = Number(value || 0)

  if (symbol === 'TRY' || symbol === 'USD') {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: symbol,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  }

  return `${new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: assetQuantityDigits(symbol),
  }).format(amount)} ${symbol}`
}

export function formatSignedAssetQuantity(value, asset, locale = 'tr-TR') {
  const numeric = Number(value || 0)
  const formatted = formatAssetQuantity(numeric, asset, locale)
  return numeric > 0 ? `+${formatted}` : formatted
}

export function formatAssetNumber(value, asset, locale = 'tr-TR') {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: assetQuantityDigits(asset),
  }).format(Number(value || 0))
}

export function formatAssetUnitPrice(value, quoteAsset, locale = 'tr-TR') {
  const symbol = String(quoteAsset || '').toUpperCase()
  const amount = Number(value || 0)

  if (symbol === 'TRY' || symbol === 'USD') {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: symbol,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  }

  return `${new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: assetQuantityDigits(symbol),
  }).format(amount)} ${symbol}`
}
