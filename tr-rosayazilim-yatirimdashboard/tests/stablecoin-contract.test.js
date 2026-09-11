import assert from 'node:assert/strict'
import test from 'node:test'
import {
  ASSETS,
  SETTLEMENT_ASSETS,
  TRADEABLE_ASSETS,
} from '../src/services/portfolioAnalytics.js'
import {
  assertTransactionRequestShape,
  normalizeTransaction,
  replayTransactionBalances,
} from '../src/services/portfolioTransactions.js'

const USER_ID = '10000000-0000-4000-8000-000000000001'
const ACCOUNT_ID = '20000000-0000-4000-8000-000000000001'

function transaction(id, input) {
  return normalizeTransaction(
    {
      id,
      transaction_at: '2026-09-11T12:00:00.000Z',
      usd_try: 48.5,
      fee_usd: 0,
      ...input,
    },
    USER_ID,
    ACCOUNT_ID,
  )
}

test('asset taxonomy treats stablecoins as both tradeable and settlement assets', () => {
  assert.deepEqual(TRADEABLE_ASSETS, ['BTC', 'ETH', 'URA', 'USDT', 'USDC'])
  assert.deepEqual(SETTLEMENT_ASSETS, ['USD', 'TRY', 'USDT', 'USDC'])
  assert.ok(ASSETS.includes('USDT'))
  assert.ok(ASSETS.includes('USDC'))
  assert.equal(new Set(ASSETS).size, ASSETS.length)
})

test('USDT and USDC are accepted as cash, buy targets, buy sources and sell sources', () => {
  const cashInUsdt = transaction('30000000-0000-4000-8000-000000000001', {
    transaction_type: 'CASH_IN',
    target_asset: 'USDT',
    target_quantity: 1000,
    price_currency: 'USDT',
    target_unit_price: 0.9995,
    gross_usd: 999.5,
    net_usd: 999.5,
  })
  const buyUsdtFromTry = transaction('30000000-0000-4000-8000-000000000002', {
    transaction_type: 'BUY',
    source_asset: 'TRY',
    source_quantity: 4_850,
    target_asset: 'USDT',
    target_quantity: 100,
    price_currency: 'TRY',
    source_unit_price: 1,
    target_unit_price: 1,
    gross_usd: 100,
    net_usd: 100,
  })
  const buyBtcFromUsdt = transaction('30000000-0000-4000-8000-000000000003', {
    transaction_type: 'BUY',
    source_asset: 'USDT',
    source_quantity: 250,
    target_asset: 'BTC',
    target_quantity: 0.0025,
    price_currency: 'USDT',
    source_unit_price: 0.9995,
    target_unit_price: 99_950,
    gross_usd: 249.875,
    net_usd: 249.875,
  })
  const sellUsdcToUsd = transaction('30000000-0000-4000-8000-000000000004', {
    transaction_type: 'SELL',
    source_asset: 'USDC',
    source_quantity: 100,
    target_asset: 'USD',
    target_quantity: 100.02,
    price_currency: 'USD',
    source_unit_price: 1.0002,
    target_unit_price: 1,
    gross_usd: 100.02,
    net_usd: 100.02,
  })
  const sellBtcToUsdc = transaction('30000000-0000-4000-8000-000000000005', {
    transaction_type: 'SELL',
    source_asset: 'BTC',
    source_quantity: 0.001,
    target_asset: 'USDC',
    target_quantity: 100,
    price_currency: 'USDC',
    source_unit_price: 100_020,
    target_unit_price: 1.0002,
    gross_usd: 100.02,
    net_usd: 100.02,
  })

  for (const row of [cashInUsdt, buyUsdtFromTry, buyBtcFromUsdt, sellUsdcToUsd, sellBtcToUsdc]) {
    assert.doesNotThrow(() => assertTransactionRequestShape(row))
  }
})

test('stablecoin balance replay remains quantity based', () => {
  const rows = [
    transaction('30000000-0000-4000-8000-000000000011', {
      transaction_type: 'CASH_IN',
      target_asset: 'USDT',
      target_quantity: 1000,
      price_currency: 'USDT',
      target_unit_price: 1,
      gross_usd: 1000,
      net_usd: 1000,
    }),
    transaction('30000000-0000-4000-8000-000000000012', {
      transaction_type: 'BUY',
      source_asset: 'USDT',
      source_quantity: 250,
      target_asset: 'ETH',
      target_quantity: 0.05,
      price_currency: 'USDT',
      source_unit_price: 1,
      target_unit_price: 5000,
      gross_usd: 250,
      net_usd: 250,
    }),
  ]

  rows.forEach(assertTransactionRequestShape)
  const replay = replayTransactionBalances(rows)
  assert.equal(replay.valid, true)
  assert.equal(replay.balances.USDT, 750)
  assert.equal(replay.balances.ETH, 0.05)
  assert.equal(replay.balances.USDC, 0)
})
