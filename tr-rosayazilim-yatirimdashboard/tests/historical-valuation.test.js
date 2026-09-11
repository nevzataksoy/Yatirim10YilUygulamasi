import assert from 'node:assert/strict'
import test from 'node:test'
import { historicalAggregate, historicalUsdToAsset } from '../src/services/historicalValuation.js'
import { buildPortfolioLedger } from '../src/services/portfolioAnalytics.js'

function closeTo(actual, expected, tolerance = 1e-8) {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `expected ${actual} to be within ${tolerance} of ${expected}`,
  )
}

function row(sequence, input) {
  return {
    id: `historical-${sequence}`,
    transaction_at: `2026-09-01T${String(sequence).padStart(2, '0')}:00:00.000Z`,
    fee_usd: 0,
    metadata: {},
    ...input,
  }
}

test('historical TRY display uses the transaction USD/TRY rate instead of a current quote', () => {
  const transaction = row(1, {
    transaction_type: 'CASH_IN',
    target_asset: 'TRY',
    target_quantity: 5000,
    usd_try: 50,
    gross_usd: 100,
    net_usd: 100,
  })

  closeTo(historicalUsdToAsset(transaction, transaction.gross_usd, 'TRY'), 5000)

  const hypotheticalCurrentUsdTry = 50.66
  assert.notEqual(transaction.gross_usd * hypotheticalCurrentUsdTry, 5000)
})

test('historical stablecoin display uses the stored transaction-time peg rate', () => {
  const transaction = row(2, {
    transaction_type: 'CASH_IN',
    target_asset: 'USDT',
    target_quantity: 1000,
    gross_usd: 998,
    net_usd: 998,
    metadata: { stablecoin_usd_rates: { USDT: 0.998 } },
  })

  closeTo(historicalUsdToAsset(transaction, 998, 'USDT'), 1000)
  assert.equal(historicalUsdToAsset(transaction, 998, 'USDC'), null)
})

test('historical aggregate converts each transaction at its own rate before summing', () => {
  const rows = [
    row(3, { usd_try: 40, gross_usd: 100 }),
    row(4, { usd_try: 50, gross_usd: 100 }),
  ]

  closeTo(historicalAggregate(rows, (tx) => tx.gross_usd, 'TRY'), 9000)
  closeTo(historicalAggregate(rows, (tx) => tx.gross_usd, 'USD'), 200)
})

test('historical TRY cost basis follows capital through a BUY without current FX revaluation', () => {
  const transactions = [
    row(5, {
      transaction_type: 'CASH_IN',
      target_asset: 'TRY',
      target_quantity: 5000,
      usd_try: 50,
      gross_usd: 100,
      net_usd: 100,
    }),
    row(6, {
      transaction_type: 'BUY',
      source_asset: 'TRY',
      source_quantity: 2000,
      target_asset: 'BTC',
      target_quantity: 0.001,
      usd_try: 50,
      gross_usd: 40,
      net_usd: 40,
    }),
  ]

  const ledger = buildPortfolioLedger(transactions)
  closeTo(ledger.assets.TRY.historicalCostBasis.TRY, 3000)
  closeTo(ledger.assets.BTC.historicalCostBasis.TRY, 2000)
  closeTo(ledger.assets.BTC.costBasisUsd, 40)
  closeTo(ledger.historical.cashIn.TRY, 5000)
  closeTo(ledger.historical.netContributed.TRY, 5000)
})
