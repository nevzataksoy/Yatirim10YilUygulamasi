import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getSupabaseClient } from '@/services/supabase'
import { demoDecisions, demoHealth, demoMarket, demoValidation } from '@/services/demoData'
import { useAuthStore } from './auth'

export const useEngineStore = defineStore('engine', () => {
  const market = ref([])
  const decisions = ref([])
  const health = ref([])
  const validation = ref([])
  const loading = ref(false)
  const lastSyncAt = ref(null)
  const lastError = ref('')
  const auth = useAuthStore()

  const readiness = computed(
    () => validation.value.find((item) => item.validation_type === 'SHADOW_READINESS') || null,
  )

  function loadDemo() {
    market.value = demoMarket.map((item) => ({ ...item }))
    decisions.value = demoDecisions.map((item) => ({ ...item }))
    health.value = demoHealth.map((item) => ({ ...item }))
    validation.value = demoValidation.map((item) => ({ ...item }))
    lastSyncAt.value = new Date().toISOString()
  }

  function reset() {
    market.value = []
    decisions.value = []
    health.value = []
    validation.value = []
    lastSyncAt.value = null
    lastError.value = ''
  }

  async function sync() {
    if (!auth.authenticated) return
    if (auth.isDemo) {
      loadDemo()
      return
    }

    const client = getSupabaseClient()
    if (!client) return

    loading.value = true
    lastError.value = ''
    try {
      const [marketResult, decisionsResult, healthResult, validationResult] = await Promise.all([
        client.from('market_snapshot').select('*'),
        client.from('decision_snapshot').select('*'),
        client.from('engine_health_snapshot').select('*'),
        client.from('model_validation_snapshot').select('*'),
      ])

      for (const result of [marketResult, decisionsResult, healthResult, validationResult]) {
        if (result.error) throw result.error
      }

      market.value = marketResult.data || []
      decisions.value = decisionsResult.data || []
      health.value = healthResult.data || []
      validation.value = validationResult.data || []
      lastSyncAt.value = new Date().toISOString()
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : 'Engine verileri alınamadı.'
      throw error
    } finally {
      loading.value = false
    }
  }

  function price(asset) {
    if (asset === 'USD') return 1
    if (asset === 'TRY') {
      const fx = market.value.find((item) => item.symbol === 'USD/TRY')?.value || 0
      return fx > 0 ? 1 / Number(fx) : 0
    }
    return Number(market.value.find((item) => item.symbol === `${asset}/USD`)?.value || 0)
  }

  return {
    market,
    decisions,
    health,
    validation,
    loading,
    lastSyncAt,
    lastError,
    readiness,
    sync,
    loadDemo,
    reset,
    price,
  }
})
