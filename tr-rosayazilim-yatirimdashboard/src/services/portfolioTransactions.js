import Decimal from 'decimal.js'
import { ASSETS } from './portfolioAnalytics.js'

const BALANCE_EPSILON = new Decimal('0.0000000001')
const NUMERIC_FIELDS = [
  'source_quantity',
  'target_quantity',
  'source_unit_price',
  'target_unit_price',
  'usd_try',
  'gross_usd',
  'fee_usd',
  'net_usd',
]
const NUMERIC_SCALES = {
  source_quantity: 12,
  target_quantity: 12,
  source_unit_price: 10,
  target_unit_price: 10,
  usd_try: 8,
  gross_usd: 8,
  fee_usd: 8,
  net_usd: 8,
}
const REQUEST_FIELDS = [
  'id',
  'user_id',
  'account_id',
  'decision_id',
  'transaction_at',
  'transaction_type',
  'source_asset',
  'target_asset',
  'price_currency',
  'platform',
  'external_ref',
  'note',
  'metadata',
  ...NUMERIC_FIELDS,
]

function nowIso() {
  return new Date().toISOString()
}

function numberOrNull(value) {
  return value === null || value === undefined || value === '' ? null : Number(value)
}

function timestamp(value) {
  const time = new Date(value || 0).getTime()
  return Number.isFinite(time) ? time : 0
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])]),
    )
  }
  return value
}

function canonicalField(field, value) {
  if (NUMERIC_FIELDS.includes(field)) {
    if (value === null || value === undefined || value === '') return null
    return new Decimal(value).toFixed(NUMERIC_SCALES[field])
  }
  if (field === 'transaction_at') return value ? new Date(value).toISOString() : null
  if (field === 'decision_id') return value === null || value === undefined ? null : String(value)
  if (field === 'metadata') return stableValue(value || {})
  return value === undefined || value === '' ? null : value
}

function emptyBalances() {
  return Object.fromEntries(ASSETS.map((asset) => [asset, new Decimal(0)]))
}

function balancesToNumbers(balances) {
  return Object.fromEntries(ASSETS.map((asset) => [asset, balances[asset].toNumber()]))
}

export function createTransactionRequestId() {
  return crypto.randomUUID()
}

export function normalizeTransaction(input, userId, accountId) {
  return {
    id: input.id || createTransactionRequestId(),
    user_id: userId,
    account_id: accountId,
    decision_id: input.decision_id || null,
    transaction_at: input.transaction_at || nowIso(),
    transaction_type: input.transaction_type,
    source_asset: input.source_asset || null,
    target_asset: input.target_asset || null,
    source_quantity: numberOrNull(input.source_quantity),
    target_quantity: numberOrNull(input.target_quantity),
    price_currency: input.price_currency || 'USD',
    source_unit_price: numberOrNull(input.source_unit_price),
    target_unit_price: numberOrNull(input.target_unit_price),
    usd_try: numberOrNull(input.usd_try),
    gross_usd: Number(input.gross_usd || 0),
    fee_usd: Number(input.fee_usd || 0),
    net_usd: Number(input.net_usd ?? input.gross_usd ?? 0),
    platform: input.platform || null,
    external_ref: input.external_ref || null,
    note: input.note || null,
    metadata: input.metadata || {},
    created_at: input.created_at || nowIso(),
  }
}

export function effectiveTransactions(rows) {
  const supersededIds = new Set(
    rows.map((tx) => tx.metadata?.supersedes_transaction_id).filter(Boolean),
  )
  return rows.filter((tx) => !supersededIds.has(tx.id) && !tx.metadata?.cancelled_at)
}

export function transactionsForAccount(rows, accountId) {
  return rows.filter((tx) => tx.account_id === accountId)
}

export function sortTransactionsChronologically(rows) {
  return [...rows].sort((a, b) => {
    const byTransaction = timestamp(a.transaction_at) - timestamp(b.transaction_at)
    if (byTransaction !== 0) return byTransaction
    const byCreated = timestamp(a.created_at) - timestamp(b.created_at)
    if (byCreated !== 0) return byCreated
    return String(a.id || '').localeCompare(String(b.id || ''))
  })
}

export function replayTransactionBalances(rows) {
  const balances = emptyBalances()

  for (const tx of sortTransactionsChronologically(rows)) {
    const sourceAsset = tx.source_asset
    const sourceQuantity = new Decimal(tx.source_quantity || 0)

    if (sourceAsset && sourceQuantity.gt(0)) {
      const available = balances[sourceAsset] || new Decimal(0)
      if (sourceQuantity.minus(available).gt(BALANCE_EPSILON)) {
        return {
          valid: false,
          transaction: tx,
          asset: sourceAsset,
          required: sourceQuantity.toNumber(),
          available: available.toNumber(),
          balances: balancesToNumbers(balances),
        }
      }
      balances[sourceAsset] = available.minus(sourceQuantity)
      if (balances[sourceAsset].abs().lte(BALANCE_EPSILON)) balances[sourceAsset] = new Decimal(0)
    }

    const targetAsset = tx.target_asset
    const targetQuantity = new Decimal(tx.target_quantity || 0)
    if (targetAsset && targetQuantity.gt(0)) {
      balances[targetAsset] = (balances[targetAsset] || new Decimal(0)).plus(targetQuantity)
    }
  }

  return { valid: true, balances: balancesToNumbers(balances) }
}

export function assertTransactionRequestShape(row) {
  const sourceQuantity = new Decimal(row.source_quantity || 0)
  const targetQuantity = new Decimal(row.target_quantity || 0)
  const sourceAsset = row.source_asset
  const targetAsset = row.target_asset

  if (!row.id || !row.user_id || !row.account_id) {
    throw new Error('İşlem kimliği, kullanıcı ve yatırım hesabı zorunludur.')
  }
  if (!ASSETS.includes(sourceAsset) && sourceAsset !== null) {
    throw new Error(`Desteklenmeyen kaynak varlık: ${sourceAsset}`)
  }
  if (!ASSETS.includes(targetAsset) && targetAsset !== null) {
    throw new Error(`Desteklenmeyen hedef varlık: ${targetAsset}`)
  }
  if (sourceAsset && targetAsset && sourceAsset === targetAsset) {
    throw new Error('Kaynak ve hedef varlık farklı olmalıdır.')
  }
  if (sourceQuantity.isNegative() || targetQuantity.isNegative()) {
    throw new Error('İşlem miktarları negatif olamaz.')
  }

  if (row.metadata?.cancelled_at) {
    if (!row.metadata?.supersedes_transaction_id || sourceQuantity.gt(0) || targetQuantity.gt(0)) {
      throw new Error(
        'İptal revizyonu yalnız önceki kayıt bağı ve sıfır bakiye etkisi içermelidir.',
      )
    }
    return row
  }

  const cashAssets = ['TRY', 'USD']
  const investmentAssets = ['BTC', 'ETH', 'URA']
  const hasSource = sourceAsset && sourceQuantity.gt(0)
  const hasTarget = targetAsset && targetQuantity.gt(0)

  switch (row.transaction_type) {
    case 'OPENING':
      if (hasSource || !hasTarget)
        throw new Error('OPENING yalnız pozitif hedef bakiyesi eklemelidir.')
      break
    case 'CASH_IN':
      if (hasSource || !hasTarget || !cashAssets.includes(targetAsset))
        throw new Error('CASH_IN yalnız TRY veya USD nakit bakiyesi eklemelidir.')
      break
    case 'CASH_OUT':
      if (!hasSource || hasTarget || !cashAssets.includes(sourceAsset))
        throw new Error('CASH_OUT yalnız TRY veya USD nakit bakiyesinden düşmelidir.')
      break
    case 'BUY':
      if (
        !hasSource ||
        !hasTarget ||
        !cashAssets.includes(sourceAsset) ||
        !investmentAssets.includes(targetAsset)
      )
        throw new Error('BUY, TRY/USD nakitten BTC/ETH/URA varlığına yapılmalıdır.')
      break
    case 'SELL':
    case 'EXIT':
      if (
        !hasSource ||
        !hasTarget ||
        !investmentAssets.includes(sourceAsset) ||
        !cashAssets.includes(targetAsset)
      )
        throw new Error('SELL/EXIT, BTC/ETH/URA varlığından TRY/USD nakde yapılmalıdır.')
      break
    case 'CONVERSION':
      if (!hasSource || !hasTarget)
        throw new Error('CONVERSION pozitif kaynak ve hedef miktarlarını birlikte içermelidir.')
      break
    default:
      throw new Error(`Desteklenmeyen işlem tipi: ${row.transaction_type || '-'}`)
  }

  return row
}

export function transactionRequestFingerprint(row) {
  return JSON.stringify(
    Object.fromEntries(REQUEST_FIELDS.map((field) => [field, canonicalField(field, row[field])])),
  )
}

export function assertIdempotentTransactionMatch(existing, requested) {
  if (transactionRequestFingerprint(existing) !== transactionRequestFingerprint(requested)) {
    throw new Error(
      `İşlem kimliği ${requested.id} daha önce farklı içerikle kullanılmış. Kayıt güvenli biçimde durduruldu.`,
    )
  }
  return existing
}

export function mergeUniqueTransactions(currentRows, incomingRows) {
  const merged = [...currentRows]
  const byId = new Map(merged.map((row) => [row.id, row]))

  for (const row of incomingRows) {
    const existing = byId.get(row.id)
    if (existing) {
      assertIdempotentTransactionMatch(existing, row)
      continue
    }
    merged.unshift(row)
    byId.set(row.id, row)
  }

  return merged
}
