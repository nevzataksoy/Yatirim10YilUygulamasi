import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getSecureValue, setSecureValue } from '@/services/secureStorage'

export const DISPLAY_ASSETS = ['USD', 'TRY', 'BTC', 'ETH']
const DISPLAY_ASSET_KEY = 'ui:display-asset'

function initialDisplayAsset() {
  const stored = getSecureValue(DISPLAY_ASSET_KEY, 'USD')
  return DISPLAY_ASSETS.includes(stored) ? stored : 'USD'
}

export const useUiStore = defineStore('ui', () => {
  const displayAsset = ref(initialDisplayAsset())

  function setDisplayAsset(asset) {
    if (!DISPLAY_ASSETS.includes(asset)) return
    displayAsset.value = asset
    setSecureValue(DISPLAY_ASSET_KEY, asset)
  }

  return {
    displayAsset,
    setDisplayAsset,
  }
})
