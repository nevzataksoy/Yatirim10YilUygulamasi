import { computed } from 'vue'
// import { useEngineStore } from '@/stores/engine'
import { useDisplayQuoteStore } from '@/stores/displayQuotes'

import { useUiStore } from '@/stores/ui'

function decimalsFor(asset) {
  if (asset === 'BTC') return 8
  if (asset === 'ETH') return 6
  return 2
}

export function useDisplayCurrency() {
  // const engine = useEngineStore()
  const displayQuotes = useDisplayQuoteStore()
  const ui = useUiStore()

  const displayAsset = computed(() => ui.displayAsset)

  function priceUsd(asset) {
    return displayQuotes.priceUsd(asset)
  }

  // function convertUsd(value, asset = displayAsset.value) {
  //   const usd = Number(value || 0)
  //   if (asset === 'USD') return usd

  //   const assetPriceUsd = Number(engine.price(asset) || 0)
  //   return assetPriceUsd > 0 ? usd / assetPriceUsd : 0
  // }
  function convertUsd(value, asset = displayAsset.value) {
    return displayQuotes.convertUsd(value, asset)
  }

  function formatDisplay(value, asset = displayAsset.value) {
    const converted = convertUsd(value, asset)

    if (asset === 'USD' || asset === 'TRY' || asset === 'EUR') {
      return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: asset,
        maximumFractionDigits: 2,
      }).format(converted)
    }

    return `${new Intl.NumberFormat('tr-TR', {
      maximumFractionDigits: decimalsFor(asset),
    }).format(converted)} ${asset}`
  }

  return {
    displayAsset,
    priceUsd,
    convertUsd,
    formatDisplay,
  }
}
