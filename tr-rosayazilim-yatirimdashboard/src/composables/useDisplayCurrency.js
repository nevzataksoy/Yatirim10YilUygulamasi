import { computed } from 'vue'
import { useDisplayQuoteStore } from '@/stores/displayQuotes'
import { historicalAggregate, historicalUsdToAsset } from '@/services/historicalValuation'
import { useUiStore } from '@/stores/ui'

function decimalsFor(asset) {
  if (asset === 'BTC') return 8
  if (asset === 'ETH' || asset === 'USDT' || asset === 'USDC') return 6
  return 2
}

export function useDisplayCurrency() {
  const displayQuotes = useDisplayQuoteStore()
  const ui = useUiStore()

  const displayAsset = computed(() => ui.displayAsset)

  function priceUsd(asset) {
    return displayQuotes.priceUsd(asset)
  }

  function convertUsd(value, asset = displayAsset.value) {
    return displayQuotes.convertUsd(value, asset)
  }

  function formatAssetValue(value, asset = displayAsset.value) {
    const numeric = Number(value || 0)

    if (asset === 'USD' || asset === 'TRY' || asset === 'EUR') {
      return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: asset,
        maximumFractionDigits: 2,
      }).format(numeric)
    }

    return `${new Intl.NumberFormat('tr-TR', {
      maximumFractionDigits: decimalsFor(asset),
    }).format(numeric)} ${asset}`
  }

  function formatDisplay(value, asset = displayAsset.value) {
    return formatAssetValue(convertUsd(value, asset), asset)
  }

  function historicalValue(value, transaction, asset = displayAsset.value) {
    const historical = historicalUsdToAsset(transaction, value, asset)
    return historical === null ? convertUsd(value, asset) : historical
  }

  function formatHistorical(value, transaction, asset = displayAsset.value) {
    return formatAssetValue(historicalValue(value, transaction, asset), asset)
  }

  function historicalAggregateValue(rows, valueSelector, asset = displayAsset.value) {
    const historical = historicalAggregate(rows, valueSelector, asset)
    if (historical !== null) return historical

    const usdTotal = (rows || []).reduce((sum, row) => sum + Number(valueSelector(row) || 0), 0)
    return convertUsd(usdTotal, asset)
  }

  return {
    displayAsset,
    priceUsd,
    convertUsd,
    formatAssetValue,
    formatDisplay,
    historicalValue,
    formatHistorical,
    historicalAggregateValue,
  }
}
