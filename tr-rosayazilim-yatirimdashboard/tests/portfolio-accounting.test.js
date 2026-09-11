import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPortfolioLedger } from '../src/services/portfolioAnalytics.js'

function closeTo(actual, expected, tolerance = 1e-8) {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `expected ${actual} to be within ${tolerance} of ${expected}`,
  )
}

function tx(sequence, input) {
  return {
    id: `accounting-${sequence}`,
    transaction_at: `2026-09-11T${String(sequence).padStart(2, '0')}:00:00.000Z`,
    fee_usd: 0,
    metadata: {},
    ...input,
  }
}

function reconciliation(ledger, prices) {
  const marketValue = Object.values(ledger.assets).reduce(
    (sum, item) => sum + item.quantity * Number(prices[item.asset] || 0),
    0,
  )
  const remainingBasis = Object.values(ledger.assets).reduce(
    (sum, item) => sum + item.costBasisUsd,
    0,
  )
  const unrealizedPnl = marketValue - remainingBasis
  const totalPnl = ledger.realizedPnlUsd + unrealizedPnl
  return { marketValue, remainingBasis, unrealizedPnl, totalPnl }
}

test('realized profit stays separate from contributed capital and remains in portfolio equity', () => {
  const ledger = buildPortfolioLedger([
    tx(1, {
      transaction_type: 'CASH_IN',
      target_asset: 'USD',
      target_quantity: 100,
      usd_try: 50,
      gross_usd: 100,
      net_usd: 100,
    }),
    tx(2, {
      transaction_type: 'BUY',
      source_asset: 'USD',
      source_quantity: 100,
      target_asset: 'BTC',
      target_quantity: 0.001,
      usd_try: 50,
      gross_usd: 99,
      fee_usd: 1,
      net_usd: 99,
      target_unit_price: 99_000,
    }),
    tx(3, {
      transaction_type: 'SELL',
      source_asset: 'BTC',
      source_quantity: 0.001,
      target_asset: 'USD',
      target_quantity: 120,
      usd_try: 50,
      source_unit_price: 121_000,
      target_unit_price: 1,
      gross_usd: 121,
      fee_usd: 1,
      net_usd: 120,
    }),
  ])

  closeTo(ledger.netContributedUsd, 100)
  closeTo(ledger.realizedPnlUsd, 20)
  closeTo(ledger.totalFeesUsd, 2)
  closeTo(ledger.assets.USD.quantity, 120)

  const result = reconciliation(ledger, { USD: 1 })
  closeTo(result.marketValue, 120)
  closeTo(result.unrealizedPnl, 0)
  closeTo(result.totalPnl, 20)
  closeTo(result.marketValue, ledger.netContributedUsd + result.totalPnl)
})

test('conversion crystallizes source PnL and starts target basis at transaction-time fair value', () => {
  const ledger = buildPortfolioLedger([
    tx(10, {
      transaction_type: 'CASH_IN',
      target_asset: 'USD',
      target_quantity: 100,
      usd_try: 50,
      gross_usd: 100,
      net_usd: 100,
    }),
    tx(11, {
      transaction_type: 'BUY',
      source_asset: 'USD',
      source_quantity: 100,
      target_asset: 'BTC',
      target_quantity: 1,
      usd_try: 50,
      gross_usd: 100,
      net_usd: 100,
      target_unit_price: 100,
    }),
    tx(12, {
      transaction_type: 'CONVERSION',
      source_asset: 'BTC',
      source_quantity: 1,
      target_asset: 'ETH',
      target_quantity: 2,
      source_unit_price: 120,
      target_unit_price: 60,
      usd_try: 50,
      gross_usd: 120,
      net_usd: 120,
    }),
  ])

  closeTo(ledger.netContributedUsd, 100)
  closeTo(ledger.realizedPnlUsd, 20)
  closeTo(ledger.assets.BTC.quantity, 0)
  closeTo(ledger.assets.ETH.quantity, 2)
  closeTo(ledger.assets.ETH.costBasisUsd, 120)

  const result = reconciliation(ledger, { ETH: 60 })
  closeTo(result.marketValue, 120)
  closeTo(result.unrealizedPnl, 0)
  closeTo(result.marketValue, ledger.netContributedUsd + result.totalPnl)
})

test('cash withdrawal crystallizes FX difference instead of contaminating contributed capital', () => {
  const ledger = buildPortfolioLedger([
    tx(20, {
      transaction_type: 'CASH_IN',
      target_asset: 'TRY',
      target_quantity: 1000,
      target_unit_price: 1 / 50,
      usd_try: 50,
      gross_usd: 20,
      net_usd: 20,
    }),
    tx(21, {
      transaction_type: 'CASH_OUT',
      source_asset: 'TRY',
      source_quantity: 500,
      source_unit_price: 1 / 100,
      usd_try: 100,
      gross_usd: 5,
      net_usd: -5,
    }),
  ])

  closeTo(ledger.netContributedUsd, 15)
  closeTo(ledger.realizedPnlUsd, -5)
  closeTo(ledger.assets.TRY.quantity, 500)
  closeTo(ledger.assets.TRY.costBasisUsd, 10)
  closeTo(ledger.historical.realizedPnl.TRY, 0)
  closeTo(ledger.historical.netContributed.TRY, 500)

  const result = reconciliation(ledger, { TRY: 1 / 100 })
  closeTo(result.marketValue, 5)
  closeTo(result.unrealizedPnl, -5)
  closeTo(result.totalPnl, -10)
  closeTo(result.marketValue, ledger.netContributedUsd + result.totalPnl)
})

test('stablecoin can be bought and sold with real transaction-time prices and no synthetic one-dollar peg', () => {
  const buyOnly = buildPortfolioLedger([
    tx(30, {
      transaction_type: 'CASH_IN',
      target_asset: 'USD',
      target_quantity: 100,
      usd_try: 50,
      gross_usd: 100,
      net_usd: 100,
    }),
    tx(31, {
      transaction_type: 'BUY',
      source_asset: 'USD',
      source_quantity: 99,
      target_asset: 'USDT',
      target_quantity: 100,
      target_unit_price: 0.99,
      usd_try: 50,
      gross_usd: 99,
      net_usd: 99,
    }),
  ])

  closeTo(buyOnly.assets.USDT.quantity, 100)
  closeTo(buyOnly.assets.USDT.costBasisUsd, 99)
  closeTo(buyOnly.assets.USDT.historicalCostBasis.USDT, 100)

  const ledger = buildPortfolioLedger([
    tx(30, {
      transaction_type: 'CASH_IN',
      target_asset: 'USD',
      target_quantity: 100,
      usd_try: 50,
      gross_usd: 100,
      net_usd: 100,
    }),
    tx(31, {
      transaction_type: 'BUY',
      source_asset: 'USD',
      source_quantity: 99,
      target_asset: 'USDT',
      target_quantity: 100,
      target_unit_price: 0.99,
      usd_try: 50,
      gross_usd: 99,
      net_usd: 99,
    }),
    tx(32, {
      transaction_type: 'SELL',
      source_asset: 'USDT',
      source_quantity: 100,
      target_asset: 'USD',
      target_quantity: 101,
      source_unit_price: 1.01,
      target_unit_price: 1,
      usd_try: 50,
      gross_usd: 101,
      net_usd: 101,
    }),
  ])

  closeTo(ledger.netContributedUsd, 100)
  closeTo(ledger.realizedPnlUsd, 2)
  closeTo(ledger.assets.USDT.quantity, 0)
  closeTo(ledger.assets.USD.quantity, 102)

  const result = reconciliation(ledger, { USD: 1 })
  closeTo(result.marketValue, 102)
  closeTo(result.unrealizedPnl, 0)
  closeTo(result.marketValue, ledger.netContributedUsd + result.totalPnl)
})
