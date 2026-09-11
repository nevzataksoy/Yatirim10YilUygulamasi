import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildInstitutionDistribution,
  buildInstitutionLedgers,
  resolveTransactionInstitution,
} from '../src/services/portfolioInstitutionAnalytics.js'
import {
  assertIdempotentTransactionMatch,
  normalizeTransaction,
} from '../src/services/portfolioTransactions.js'

const institutions = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    name: 'Midas',
    institution_type: 'BROKER',
    country_code: 'TR',
    is_active: true,
  },
  {
    id: '22222222-2222-4222-8222-222222222222',
    name: 'Coinbase',
    institution_type: 'EXCHANGE',
    country_code: 'US',
    is_active: true,
  },
]

function tx(sequence, input) {
  return {
    id: `institution-${sequence}`,
    transaction_at: `2026-09-11T${String(sequence).padStart(2, '0')}:00:00.000Z`,
    fee_usd: 0,
    metadata: {},
    ...input,
  }
}

test('institution_id is canonical even when the historical platform snapshot was renamed', () => {
  const resolved = resolveTransactionInstitution(
    {
      institution_id: institutions[0].id,
      platform: 'Eski Midas Adı',
    },
    institutions,
  )

  assert.equal(resolved.key, `id:${institutions[0].id}`)
  assert.equal(resolved.name, 'Midas')
  assert.equal(resolved.institutionType, 'BROKER')
  assert.equal(resolved.resolution, 'institution_id')
  assert.equal(resolved.legacy, false)
})

test('legacy platform text resolves to the canonical institution without merging unknown names', () => {
  const known = resolveTransactionInstitution({ platform: '  Midas ' }, institutions)
  const unknown = resolveTransactionInstitution({ platform: 'Başka Borsa' }, institutions)
  const empty = resolveTransactionInstitution({}, institutions)

  assert.equal(known.institutionId, institutions[0].id)
  assert.equal(known.resolution, 'platform_name_fallback')
  assert.equal(unknown.institutionId, null)
  assert.equal(unknown.name, 'Başka Borsa')
  assert.equal(unknown.resolution, 'unmapped_platform')
  assert.equal(empty.name, 'Kurum Belirtilmemiş')
  assert.equal(empty.unassigned, true)
})

test('transaction normalization preserves institution_id without making DB trigger enrichment an idempotency mismatch', () => {
  const baseInput = {
    id: '33333333-3333-4333-8333-333333333333',
    transaction_type: 'CASH_IN',
    target_asset: 'USD',
    target_quantity: 100,
    gross_usd: 100,
    net_usd: 100,
    usd_try: 50,
    platform: 'Midas',
    transaction_at: '2026-09-11T12:00:00.000Z',
  }
  const request = normalizeTransaction(baseInput, 'user-1', 'account-1')
  const revisionInput = normalizeTransaction(
    { ...baseInput, institution_id: institutions[0].id },
    'user-1',
    'account-1',
  )

  assert.equal(request.institution_id, null)
  assert.equal(revisionInput.institution_id, institutions[0].id)
  assert.doesNotThrow(() =>
    assertIdempotentTransactionMatch(
      { ...request, institution_id: institutions[0].id },
      request,
    ),
  )
})

test('the same asset held at two institutions remains separated by institution ledger', () => {
  const rows = [
    tx(1, {
      institution_id: institutions[0].id,
      platform: 'Midas',
      transaction_type: 'OPENING',
      target_asset: 'BTC',
      target_quantity: 0.01,
      gross_usd: 600,
      net_usd: 600,
      usd_try: 50,
    }),
    tx(2, {
      institution_id: institutions[1].id,
      platform: 'Coinbase',
      transaction_type: 'OPENING',
      target_asset: 'BTC',
      target_quantity: 0.02,
      gross_usd: 1200,
      net_usd: 1200,
      usd_try: 50,
    }),
  ]

  const groups = buildInstitutionLedgers(rows, institutions)
  assert.equal(groups.length, 2)
  assert.equal(groups.find((item) => item.name === 'Midas').ledger.assets.BTC.quantity, 0.01)
  assert.equal(groups.find((item) => item.name === 'Coinbase').ledger.assets.BTC.quantity, 0.02)
})

test('institution distribution reports value, allocation and per-ledger cost without summing unlike quantities', () => {
  const rows = [
    tx(10, {
      institution_id: institutions[0].id,
      platform: 'Midas',
      transaction_type: 'OPENING',
      target_asset: 'URA',
      target_quantity: 10,
      gross_usd: 400,
      net_usd: 400,
      usd_try: 50,
    }),
    tx(11, {
      institution_id: institutions[1].id,
      platform: 'Coinbase',
      transaction_type: 'OPENING',
      target_asset: 'USDT',
      target_quantity: 500,
      target_unit_price: 1,
      gross_usd: 500,
      net_usd: 500,
      usd_try: 50,
      metadata: { stablecoin_usd_rates: { USDT: 1 } },
    }),
  ]

  const prices = { URA: 50, USDT: 1 }
  const distribution = buildInstitutionDistribution({
    transactions: rows,
    institutions,
    priceUsd: (asset) => prices[asset] || 0,
  })

  assert.equal(distribution.length, 2)
  const midas = distribution.find((item) => item.name === 'Midas')
  const coinbase = distribution.find((item) => item.name === 'Coinbase')

  assert.equal(midas.assets.length, 1)
  assert.equal(midas.assets[0].asset, 'URA')
  assert.equal(midas.assets[0].quantity, 10)
  assert.equal(midas.valuation.currentValueUsd, 500)
  assert.equal(midas.valuation.costBasisUsd, 400)
  assert.equal(midas.valuation.unrealizedPnlUsd, 100)
  assert.equal(midas.allocationPct, 50)

  assert.equal(coinbase.assets[0].asset, 'USDT')
  assert.equal(coinbase.assets[0].quantity, 500)
  assert.equal(coinbase.valuation.currentValueUsd, 500)
  assert.equal(coinbase.allocationPct, 50)
})

test('a missing live quote marks allocation incomplete instead of inventing a value', () => {
  const rows = [
    tx(20, {
      institution_id: institutions[0].id,
      platform: 'Midas',
      transaction_type: 'OPENING',
      target_asset: 'URA',
      target_quantity: 10,
      gross_usd: 400,
      net_usd: 400,
      usd_try: 50,
    }),
  ]

  const [row] = buildInstitutionDistribution({
    transactions: rows,
    institutions,
    priceUsd: () => 0,
  })

  assert.equal(row.valuation.valuationComplete, false)
  assert.equal(row.valuation.currentValueUsd, null)
  assert.equal(row.valuation.unrealizedPnlUsd, null)
  assert.equal(row.allocationPct, null)
})
