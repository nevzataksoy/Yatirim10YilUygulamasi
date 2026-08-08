import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getSupabaseClient } from '@/services/supabase'
import { useAuthStore } from './auth'
import { usePortfolioStore } from './portfolio'

export const INSTITUTION_TYPES = [
  { label: 'Banka', value: 'BANK' },
  { label: 'Kripto Borsası', value: 'EXCHANGE' },
  { label: 'Aracı Kurum', value: 'BROKER' },
  { label: 'Saklama Kurumu', value: 'CUSTODIAN' },
  { label: 'Fon / Yatırım Platformu', value: 'FUND_PLATFORM' },
  { label: 'Diğer', value: 'OTHER' },
]

export const useInstitutionsStore = defineStore('institutions', () => {
  const institutions = ref([])
  const mappings = ref([])
  const loading = ref(false)
  const lastError = ref('')
  const auth = useAuthStore()
  const portfolio = usePortfolioStore()

  const activeInstitutions = computed(() => institutions.value.filter((item) => item.is_active !== false))

  function typeLabel(value) {
    return INSTITUTION_TYPES.find((item) => item.value === value)?.label || 'Diğer'
  }

  function institutionsForAccount(accountId = portfolio.selectedAccountId) {
    if (!accountId) return []
    const activeIds = new Set(
      mappings.value
        .filter((item) => item.account_id === accountId && item.is_active !== false)
        .map((item) => item.institution_id),
    )
    return activeInstitutions.value.filter((item) => activeIds.has(item.id))
  }

  function optionsForAccount(accountId = portfolio.selectedAccountId) {
    return institutionsForAccount(accountId).map((item) => ({
      label: item.name,
      value: item.name,
      caption: typeLabel(item.institution_type),
      badge: item.country_code || '',
      icon: item.institution_type === 'BANK' ? 'account_balance' : 'currency_exchange',
      institutionId: item.id,
    }))
  }

  async function sync() {
    if (!auth.authenticated || auth.isDemo) return
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) return
    loading.value = true
    lastError.value = ''
    try {
      const [institutionsResult, mappingsResult] = await Promise.all([
        client
          .from('financial_institutions')
          .select('*')
          .eq('user_id', auth.user.id)
          .order('name'),
        client
          .from('investment_account_institutions')
          .select('*')
          .eq('user_id', auth.user.id),
      ])
      if (institutionsResult.error) throw institutionsResult.error
      if (mappingsResult.error) throw mappingsResult.error
      institutions.value = institutionsResult.data || []
      mappings.value = mappingsResult.data || []
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : 'Kurum sözlüğü alınamadı.'
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createInstitution({ name, institutionType, countryCode = '', website = '', note = '', accountId = null }) {
    const normalizedName = String(name || '').trim()
    const targetAccountId = accountId || portfolio.selectedAccountId
    if (!normalizedName || normalizedName.length < 2) throw new Error('Kurum adı en az 2 karakter olmalı.')
    if (!targetAccountId) throw new Error('Önce aktif portföy hesabı seçilmeli.')
    if (auth.isDemo) throw new Error('Demo modunda gerçek kurum sözlüğü oluşturulamaz.')

    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')

    let institution = institutions.value.find(
      (item) => item.name.localeCompare(normalizedName, 'tr', { sensitivity: 'accent' }) === 0,
    )

    if (!institution) {
      const { data, error } = await client
        .from('financial_institutions')
        .insert({
          user_id: auth.user.id,
          name: normalizedName,
          institution_type: institutionType || 'OTHER',
          country_code: countryCode ? countryCode.toUpperCase() : null,
          website: website || null,
          note: note || null,
        })
        .select()
        .single()
      if (error) throw error
      institution = data
      institutions.value = [...institutions.value, data].sort((a, b) => a.name.localeCompare(b.name, 'tr'))
    }

    if (institution.is_active === false) {
      const { data, error } = await client
        .from('financial_institutions')
        .update({ is_active: true })
        .eq('id', institution.id)
        .select()
        .single()
      if (error) throw error
      institution = data
      institutions.value = institutions.value.map((item) => (item.id === data.id ? data : item))
    }

    const existingMapping = mappings.value.find(
      (item) => item.account_id === targetAccountId && item.institution_id === institution.id,
    )
    if (!existingMapping || existingMapping.is_active === false) {
      const { data, error } = await client
        .from('investment_account_institutions')
        .upsert(
          {
            user_id: auth.user.id,
            account_id: targetAccountId,
            institution_id: institution.id,
            is_active: true,
          },
          { onConflict: 'account_id,institution_id' },
        )
        .select()
        .single()
      if (error) throw error
      mappings.value = [
        ...mappings.value.filter(
          (item) => !(item.account_id === targetAccountId && item.institution_id === institution.id),
        ),
        data,
      ]
    }
    return institution
  }


  async function updateInstitution(id, input) {
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')
    const payload = {
      name: String(input.name || '').trim(),
      institution_type: input.institutionType || input.institution_type || 'OTHER',
      country_code: input.countryCode || input.country_code
        ? String(input.countryCode || input.country_code).trim().toUpperCase()
        : null,
      website: input.website || null,
      note: input.note || null,
      is_active: input.is_active !== false,
    }
    if (payload.name.length < 2) throw new Error('Kurum adı en az 2 karakter olmalı.')
    const { data, error } = await client
      .from('financial_institutions')
      .update(payload)
      .eq('id', id)
      .eq('user_id', auth.user.id)
      .select()
      .single()
    if (error) throw error
    institutions.value = institutions.value.map((item) => (item.id === id ? data : item))
    return data
  }

  async function setInstitutionActive(id, active) {
    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yok.')
    const { data, error } = await client
      .from('financial_institutions')
      .update({ is_active: Boolean(active) })
      .eq('id', id)
      .select()
      .single()
    if (error) throw error
    institutions.value = institutions.value.map((item) => (item.id === id ? data : item))
    return data
  }

  async function setAccountMappingActive(accountId, institutionId, active) {
    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı yok.')
    const { data, error } = await client
      .from('investment_account_institutions')
      .upsert(
        {
          user_id: auth.user.id,
          account_id: accountId,
          institution_id: institutionId,
          is_active: Boolean(active),
        },
        { onConflict: 'account_id,institution_id' },
      )
      .select()
      .single()
    if (error) throw error
    mappings.value = [
      ...mappings.value.filter(
        (item) => !(item.account_id === accountId && item.institution_id === institutionId),
      ),
      data,
    ]
    return data
  }

  function reset() {
    institutions.value = []
    mappings.value = []
    lastError.value = ''
  }

  return {
    institutions,
    mappings,
    loading,
    lastError,
    activeInstitutions,
    typeLabel,
    institutionsForAccount,
    optionsForAccount,
    sync,
    createInstitution,
    updateInstitution,
    setInstitutionActive,
    setAccountMappingActive,
    reset,
  }
})
