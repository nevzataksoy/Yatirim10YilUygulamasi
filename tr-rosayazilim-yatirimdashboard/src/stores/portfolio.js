import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getSupabaseClient } from '@/services/supabase'
import { ASSETS, buildPortfolioLedger } from '@/services/portfolioAnalytics'
import {
  assertIdempotentTransactionMatch,
  assertTransactionRequestShape,
  effectiveTransactions,
  mergeUniqueTransactions,
  normalizeTransaction,
  replayTransactionBalances,
  transactionsForAccount,
} from '@/services/portfolioTransactions'
import {
  DEMO_DATA_REVISION,
  demoAccount,
  demoSettings,
  demoTransactions,
} from '@/services/demoData'
import { useAuthStore } from './auth'

function nowIso() {
  return new Date().toISOString()
}

function ratioToPercentage(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric * 100 : fallback
}

function percentageToRatio(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric / 100 : fallback
}

function settingsFromDatabase(row) {
  if (!row) return null
  return {
    ...row,
    btc_target_pct: ratioToPercentage(row.btc_target_pct, 37.5),
    eth_target_pct: ratioToPercentage(row.eth_target_pct, 37.5),
    ura_target_pct: ratioToPercentage(row.ura_target_pct, 25),
    btc_eth_conversion_pct: ratioToPercentage(row.btc_eth_conversion_pct, 50),
    ura_usd_conversion_pct: ratioToPercentage(row.ura_usd_conversion_pct, 50),
  }
}

function settingsToDatabase(settings, userId) {
  return {
    user_id: userId,
    monthly_budget_usd: Number(settings.monthly_budget_usd || 0),
    start_date: settings.start_date || '2026-07-25',
    btc_target_pct: percentageToRatio(settings.btc_target_pct, 0.375),
    eth_target_pct: percentageToRatio(settings.eth_target_pct, 0.375),
    ura_target_pct: percentageToRatio(settings.ura_target_pct, 0.25),
    btc_eth_conversion_pct: percentageToRatio(settings.btc_eth_conversion_pct, 0.5),
    ura_usd_conversion_pct: percentageToRatio(settings.ura_usd_conversion_pct, 0.5),
    dca_day: Number(settings.dca_day || 25),
    telegram_notifications: settings.telegram_notifications !== false,
  }
}

function timestamp(value) {
  const time = new Date(value || 0).getTime()
  return Number.isFinite(time) ? time : 0
}

export const usePortfolioStore = defineStore('portfolio', () => {
  const accounts = ref([])
  const selectedAccountId = ref(null)
  const transactions = ref([])
  const settings = ref(null)
  const demoDataRevision = ref('')
  const loading = ref(false)
  const lastSyncAt = ref(null)
  const lastError = ref('')

  const auth = useAuthStore()
  const activeAccounts = computed(() =>
    accounts.value.filter((account) => account.is_active !== false),
  )
  const selectedAccount = computed(
    () =>
      activeAccounts.value.find((account) => account.id === selectedAccountId.value) ||
      activeAccounts.value.find((account) => account.is_default) ||
      activeAccounts.value[0] ||
      null,
  )

  // Audit/history list. Superseded revisions are intentionally retained here.
  const selectedTransactionHistory = computed(() => {
    if (!selectedAccountId.value) return []
    return transactionsForAccount(transactions.value, selectedAccountId.value)
  })

  // Only the latest effective revision of each transaction enters reports and ledger calculations.
  const selectedTransactions = computed(() =>
    effectiveTransactions(selectedTransactionHistory.value),
  )
  const ledger = computed(() => buildPortfolioLedger(selectedTransactions.value))
  const quantities = computed(() =>
    Object.fromEntries(ASSETS.map((asset) => [asset, ledger.value.assets[asset]?.quantity || 0])),
  )

  function findTransaction(id) {
    return transactions.value.find((tx) => tx.id === id) || null
  }

  function isSupersededTransaction(id) {
    return transactions.value.some((tx) => tx.metadata?.supersedes_transaction_id === id)
  }

  function isCancelledTransaction(txOrId) {
    const tx = typeof txOrId === 'string' ? findTransaction(txOrId) : txOrId
    return Boolean(tx?.metadata?.cancelled_at)
  }

  function transactionRevisionNumber(txOrId) {
    const tx = typeof txOrId === 'string' ? findTransaction(txOrId) : txOrId
    return Math.max(1, Number(tx?.metadata?.revision_number || 1))
  }

  function isEffectiveTransaction(id) {
    const tx = findTransaction(id)
    if (!tx || tx.account_id !== selectedAccountId.value) return false
    return !isSupersededTransaction(id) && !isCancelledTransaction(tx)
  }

  function ledgerWithoutTransaction(id) {
    return buildPortfolioLedger(selectedTransactions.value.filter((tx) => tx.id !== id))
  }

  function quantitiesWithoutTransaction(id) {
    const baseLedger = ledgerWithoutTransaction(id)
    return Object.fromEntries(
      ASSETS.map((asset) => [asset, baseLedger.assets[asset]?.quantity || 0]),
    )
  }

  function quantitiesBeforeTransaction(id, transactionAt = null) {
    const current = findTransaction(id)
    if (!current) return Object.fromEntries(ASSETS.map((asset) => [asset, 0]))

    const effective = selectedTransactions.value.filter((tx) => tx.id !== id)
    const targetTime = timestamp(transactionAt || current.transaction_at)
    const currentCreated = timestamp(current.created_at)
    const before = effective.filter((tx) => {
      const txTime = timestamp(tx.transaction_at)
      if (txTime < targetTime) return true
      if (txTime > targetTime) return false
      return timestamp(tx.created_at) < currentCreated
    })
    const replay = replayTransactionBalances(before)
    return replay.balances || Object.fromEntries(ASSETS.map((asset) => [asset, 0]))
  }

  function validateRevisionBalance(transactionId, replacement) {
    const current = findTransaction(transactionId)
    if (!current) return { valid: false, error: 'Düzenlenecek işlem bulunamadı.' }

    const candidate = normalizeTransaction(
      {
        ...current,
        ...replacement,
        id: `revision-preview:${current.id}`,
        account_id: current.account_id,
        user_id: current.user_id,
        created_at: current.created_at,
      },
      current.user_id || auth.user?.id || 'demo-user',
      current.account_id,
    )

    const replay = replayTransactionBalances([
      ...selectedTransactions.value.filter((tx) => tx.id !== current.id),
      candidate,
    ])

    if (replay.valid) return replay

    const offending = replay.transaction
    const when = offending?.transaction_at
      ? new Date(offending.transaction_at).toLocaleString('tr-TR')
      : 'bilinmeyen zaman'
    return {
      ...replay,
      error: `${replay.asset} bakiye zinciri bozuluyor. ${when} tarihli ${offending?.transaction_type || 'işlem'} için gereken ${replay.required}, kullanılabilir ${replay.available}. Revizyon sonraki işlemleri geçersiz hale getirmemeli.`,
    }
  }

  function loadDemo() {
    const cachedDemoAccounts = accounts.value.filter((account) => account.user_id === 'demo-user')
    accounts.value = cachedDemoAccounts.length ? cachedDemoAccounts : [{ ...demoAccount }]
    selectedAccountId.value =
      selectedAccountId.value &&
      accounts.value.some(
        (account) => account.id === selectedAccountId.value && account.is_active !== false,
      )
        ? selectedAccountId.value
        : accounts.value.find((account) => account.is_default)?.id || accounts.value[0]?.id || null
    settings.value = { ...demoSettings }

    if (demoDataRevision.value !== DEMO_DATA_REVISION) {
      transactions.value = demoTransactions.map((item) => ({ ...item }))
      demoDataRevision.value = DEMO_DATA_REVISION
    } else if (!transactions.value.every((item) => item.user_id === 'demo-user')) {
      transactions.value = demoTransactions.map((item) => ({ ...item }))
    }

    lastSyncAt.value = nowIso()
  }

  async function sync() {
    if (!auth.authenticated) return
    if (auth.isDemo) {
      loadDemo()
      return
    }

    const client = getSupabaseClient()
    if (!client || !auth.user?.id) return

    loading.value = true
    lastError.value = ''
    try {
      const userId = auth.user.id
      const [accountsResult, transactionsResult, settingsResult] = await Promise.all([
        client.from('investment_accounts').select('*').eq('user_id', userId).order('created_at'),
        client
          .from('portfolio_transactions')
          .select('*')
          .eq('user_id', userId)
          .order('transaction_at', { ascending: false }),
        client
          .from('user_investment_settings')
          .select('*')
          .eq('user_id', userId)
          .limit(1)
          .maybeSingle(),
      ])

      if (accountsResult.error) throw accountsResult.error
      if (transactionsResult.error) throw transactionsResult.error
      if (settingsResult.error) throw settingsResult.error

      accounts.value = accountsResult.data || []
      transactions.value = transactionsResult.data || []
      settings.value = settingsFromDatabase(settingsResult.data)
      const availableAccounts = accounts.value.filter((account) => account.is_active !== false)
      selectedAccountId.value =
        selectedAccountId.value &&
        availableAccounts.some((item) => item.id === selectedAccountId.value)
          ? selectedAccountId.value
          : availableAccounts.find((item) => item.is_default)?.id ||
            availableAccounts[0]?.id ||
            null
      lastSyncAt.value = nowIso()
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : 'Portföy eşitleme başarısız.'
      throw error
    } finally {
      loading.value = false
    }
  }

  function validateCandidateBalances(rows) {
    const byAccount = new Map()
    for (const row of rows) {
      const accountRows = byAccount.get(row.account_id) || []
      accountRows.push(row)
      byAccount.set(row.account_id, accountRows)
    }

    for (const [accountId, candidates] of byAccount) {
      const candidateIds = new Set(candidates.map((row) => row.id))
      const accountHistory = transactionsForAccount(transactions.value, accountId).filter(
        (row) => !candidateIds.has(row.id),
      )
      const replay = replayTransactionBalances(
        effectiveTransactions([...accountHistory, ...candidates]),
      )
      if (replay.valid) continue

      const when = replay.transaction?.transaction_at
        ? new Date(replay.transaction.transaction_at).toLocaleString('tr-TR')
        : 'bilinmeyen zaman'
      throw new Error(
        `${replay.asset} bakiye zinciri bozuluyor. ${when} tarihli ${replay.transaction?.transaction_type || 'işlem'} için gereken ${replay.required}, kullanılabilir ${replay.available}.`,
      )
    }
  }

  function requestedRowsInOrder(rows) {
    const byId = new Map(transactions.value.map((row) => [row.id, row]))
    return rows.map((row) => byId.get(row.id)).filter(Boolean)
  }

  async function loadExistingRetryRows(client, rows, originalError) {
    const ids = rows.map((row) => row.id)
    const { data, error } = await client.from('portfolio_transactions').select('*').in('id', ids)
    if (error || data?.length !== rows.length) throw originalError

    for (const requested of rows) {
      const existing = data.find((row) => row.id === requested.id)
      if (!existing) throw originalError
      assertIdempotentTransactionMatch(existing, requested)
    }
    return data
  }

  async function persistNormalizedTransactions(rows) {
    if (!rows.length) return []
    for (const row of rows) assertTransactionRequestShape(row)

    const existingById = new Map(transactions.value.map((row) => [row.id, row]))
    const pendingRows = []
    for (const row of rows) {
      const existing = existingById.get(row.id)
      if (existing) assertIdempotentTransactionMatch(existing, row)
      else pendingRows.push(row)
    }

    if (!pendingRows.length) return requestedRowsInOrder(rows)
    validateCandidateBalances(pendingRows)

    if (auth.isDemo) {
      transactions.value = mergeUniqueTransactions(transactions.value, pendingRows)
      lastSyncAt.value = nowIso()
      return requestedRowsInOrder(rows)
    }

    const client = getSupabaseClient()
    if (!client) throw new Error('Supabase bağlantısı yok.')
    if (!selectedAccountId.value) throw new Error('Önce yatırım hesabı oluşturulmalı.')

    const payload = pendingRows.map((row) => {
      const item = { ...row }
      delete item.created_at
      delete item.updated_at
      return item
    })

    let savedRows
    const { data, error } = await client.from('portfolio_transactions').insert(payload).select()
    if (error) {
      if (error.code !== '23505') throw error
      savedRows = await loadExistingRetryRows(client, pendingRows, error)
    } else {
      savedRows = data || []
    }

    transactions.value = mergeUniqueTransactions(transactions.value, savedRows)
    lastSyncAt.value = nowIso()
    return requestedRowsInOrder(rows)
  }

  async function persistNormalizedTransaction(row) {
    const [saved] = await persistNormalizedTransactions([row])
    return saved
  }

  async function addTransaction(input) {
    const accountId = input.account_id || selectedAccountId.value || demoAccount.id
    const row = normalizeTransaction(input, auth.user?.id || 'demo-user', accountId)
    return persistNormalizedTransaction(row)
  }

  async function reviseTransaction(
    transactionId,
    replacement,
    revisionReason = '',
    requestId = null,
  ) {
    const current = findTransaction(transactionId)
    if (!current) throw new Error('Düzenlenecek işlem bulunamadı.')
    if (current.account_id !== selectedAccountId.value)
      throw new Error('İşlem aktif yatırım hesabına ait değil.')
    if (isSupersededTransaction(current.id)) {
      throw new Error('Bu kayıt eski bir revizyon. Yalnız güncel revizyon düzenlenebilir.')
    }

    const balanceValidation = validateRevisionBalance(transactionId, replacement)
    if (!balanceValidation.valid) throw new Error(balanceValidation.error)

    const revisionRootId = current.metadata?.revision_root_id || current.id
    const revisionNumber = transactionRevisionNumber(current) + 1
    const metadata = {
      ...(current.metadata || {}),
      ...(replacement.metadata || {}),
      revision_root_id: revisionRootId,
      revision_number: revisionNumber,
      supersedes_transaction_id: current.id,
      revised_at: nowIso(),
      revision_reason: revisionReason || null,
    }

    const row = normalizeTransaction(
      {
        ...current,
        ...replacement,
        id: requestId,
        account_id: current.account_id,
        user_id: current.user_id,
        metadata,
        created_at: null,
      },
      current.user_id || auth.user?.id || 'demo-user',
      current.account_id,
    )

    return persistNormalizedTransaction(row)
  }

  async function cancelTransaction(transactionId, cancellationReason = '', requestId = null) {
    const current = findTransaction(transactionId)
    if (!current) throw new Error('İptal edilecek işlem bulunamadı.')
    if (current.account_id !== selectedAccountId.value)
      throw new Error('İşlem aktif yatırım hesabına ait değil.')
    if (!isEffectiveTransaction(current.id))
      throw new Error('Yalnız güncel ve aktif bir işlem iptal edilebilir.')

    const replay = replayTransactionBalances(
      selectedTransactions.value.filter((tx) => tx.id !== current.id),
    )
    if (!replay.valid) {
      const when = replay.transaction?.transaction_at
        ? new Date(replay.transaction.transaction_at).toLocaleString('tr-TR')
        : 'bilinmeyen zaman'
      throw new Error(
        `${replay.asset} bakiye zinciri bozuluyor. ${when} tarihli işlem için gereken ${replay.required}, kullanılabilir ${replay.available}. Önce bağlı sonraki işlemleri revize etmelisin.`,
      )
    }

    const revisionRootId = current.metadata?.revision_root_id || current.id
    const revisionNumber = transactionRevisionNumber(current) + 1
    const row = normalizeTransaction(
      {
        ...current,
        id: requestId,
        source_quantity: null,
        target_quantity: null,
        gross_usd: 0,
        fee_usd: 0,
        net_usd: 0,
        external_ref: null,
        metadata: {
          ...(current.metadata || {}),
          revision_root_id: revisionRootId,
          revision_number: revisionNumber,
          supersedes_transaction_id: current.id,
          cancelled_at: nowIso(),
          cancellation_reason: cancellationReason || null,
        },
        created_at: null,
      },
      current.user_id || auth.user?.id || 'demo-user',
      current.account_id,
    )

    return persistNormalizedTransaction(row)
  }

  async function addOpeningPositions(rows) {
    const accountId = selectedAccountId.value || demoAccount.id
    const userId = auth.user?.id || 'demo-user'
    const normalizedRows = []
    for (const row of rows) {
      if (!row.target_asset || Number(row.target_quantity) <= 0) continue
      normalizedRows.push(
        normalizeTransaction({ ...row, transaction_type: 'OPENING' }, userId, accountId),
      )
    }
    return persistNormalizedTransactions(normalizedRows)
  }

  function selectAccount(accountId) {
    const account = activeAccounts.value.find((item) => item.id === accountId)
    if (!account) throw new Error('Seçilen portföy hesabı aktif değil veya bulunamadı.')
    selectedAccountId.value = account.id
    return account
  }

  async function createAccount({ name, baseCurrency = 'USD' }) {
    const normalizedName = String(name || '').trim()
    const normalizedCurrency = String(baseCurrency || 'USD').toLocaleUpperCase('tr-TR')

    if (normalizedName.length < 2) throw new Error('Portföy hesabı adı en az 2 karakter olmalı.')
    if (normalizedName.length > 80)
      throw new Error('Portföy hesabı adı en fazla 80 karakter olabilir.')
    if (!['USD', 'TRY'].includes(normalizedCurrency))
      throw new Error('Portföy baz para birimi USD veya TRY olmalı.')
    if (
      accounts.value.some(
        (account) =>
          account.name.trim().toLocaleLowerCase('tr-TR') ===
          normalizedName.toLocaleLowerCase('tr-TR'),
      )
    )
      throw new Error('Bu adla bir portföy hesabı zaten bulunuyor.')

    const userId = auth.user?.id || 'demo-user'
    if (auth.isDemo) {
      const row = {
        id: crypto.randomUUID(),
        user_id: userId,
        name: normalizedName,
        base_currency: normalizedCurrency,
        is_default: accounts.value.length === 0,
        is_active: true,
        created_at: nowIso(),
        updated_at: nowIso(),
      }
      accounts.value = [...accounts.value, row]
      selectAccount(row.id)
      lastSyncAt.value = nowIso()
      return row
    }

    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')

    const { data, error } = await client
      .from('investment_accounts')
      .insert({
        user_id: auth.user.id,
        name: normalizedName,
        base_currency: normalizedCurrency,
        is_default: accounts.value.length === 0,
        is_active: true,
      })
      .select()
      .single()
    if (error) throw error

    accounts.value = [...accounts.value, data]
    selectAccount(data.id)
    lastSyncAt.value = nowIso()
    return data
  }

  async function saveSettings(nextSettings) {
    const merged = { ...(settings.value || {}), ...nextSettings }
    settings.value = merged
    if (auth.isDemo) return merged

    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı yok.')

    const payload = settingsToDatabase(merged, auth.user.id)
    const { data, error } = await client
      .from('user_investment_settings')
      .upsert(payload, { onConflict: 'user_id' })
      .select()
      .single()
    if (error) throw error
    settings.value = settingsFromDatabase(data)
    return settings.value
  }

  async function resetSelectedAccountTransactionHistory(confirmationPhrase) {
    const accountId = selectedAccountId.value
    if (!accountId) throw new Error('Sıfırlanacak yatırım hesabı bulunamadı.')

    if (auth.isDemo) {
      const deletedCount = transactions.value.filter((tx) => tx.account_id === accountId).length
      transactions.value = transactions.value.filter((tx) => tx.account_id !== accountId)
      lastSyncAt.value = nowIso()
      return deletedCount
    }

    const client = getSupabaseClient()
    if (!client || !auth.user?.id) throw new Error('Supabase bağlantısı veya oturum yok.')

    const { data, error } = await client.rpc('reset_portfolio_transaction_history', {
      p_account_id: accountId,
      p_confirmation_phrase: confirmationPhrase,
    })
    if (error) throw error

    transactions.value = transactions.value.filter((tx) => tx.account_id !== accountId)
    lastSyncAt.value = nowIso()
    return Number(data || 0)
  }

  function reset() {
    accounts.value = []
    selectedAccountId.value = null
    transactions.value = []
    settings.value = null
    lastSyncAt.value = null
    lastError.value = ''
  }

  return {
    accounts,
    selectedAccountId,
    transactions,
    settings,
    demoDataRevision,
    loading,
    lastSyncAt,
    lastError,
    activeAccounts,
    selectedAccount,
    selectedTransactionHistory,
    selectedTransactions,
    ledger,
    quantities,
    findTransaction,
    isSupersededTransaction,
    isCancelledTransaction,
    isEffectiveTransaction,
    transactionRevisionNumber,
    ledgerWithoutTransaction,
    quantitiesWithoutTransaction,
    quantitiesBeforeTransaction,
    validateRevisionBalance,
    sync,
    loadDemo,
    addTransaction,
    reviseTransaction,
    cancelTransaction,
    addOpeningPositions,
    selectAccount,
    createAccount,
    saveSettings,
    resetSelectedAccountTransactionHistory,
    reset,
  }
})
