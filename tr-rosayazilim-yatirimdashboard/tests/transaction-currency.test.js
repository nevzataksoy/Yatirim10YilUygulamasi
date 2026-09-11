import assert from 'node:assert/strict'
import test from 'node:test'
import {
  actualStablecoinUsdQuote,
  formatSettlementAmount,
  settlementAmountToUsd,
  settlementUsdUnitPrice,
  stablecoinRateFromMetadata,
  stablecoinRateFromTransaction,
  stablecoinRatesMetadata,
} from '../src/services/transactionCurrency.js'

test('stablecoin transaction valuation uses explicit transaction-time USD rates', () => {
  assert.equal(settlementUsdUnitPrice('USD'), 1)
  assert.equal(settlementUsdUnitPrice('TRY', { usdTry: 50 }), 0.02)
  assert.equal(settlementUsdUnitPrice('USDT', { stablecoinUsd: 0.9987 }), 0.9987)
  assert.equal(settlementUsdUnitPrice('USDC', { stablecoinUsd: 1.0004 }), 1.0004)
  assert.equal(settlementAmountToUsd(100, 'USDT', { stablecoinUsd: 0.9987 }), 99.87)
  assert.equal(settlementAmountToUsd(5000, 'TRY', { usdTry: 50 }), 100)
})

test('actual stablecoin quote never invents a one-dollar historical rate', () => {
  const quotes = {
    USDT_USD: { value: 0.9991 },
    USDC_USD: { value: 1.0002 },
  }
  assert.equal(actualStablecoinUsdQuote(quotes, 'USDT'), 0.9991)
  assert.equal(actualStablecoinUsdQuote(quotes, 'USDC'), 1.0002)
  assert.equal(actualStablecoinUsdQuote({}, 'USDT'), 0)
  assert.equal(actualStablecoinUsdQuote({}, 'USD'), 0)
})

test('stablecoin audit metadata round-trips both sides of a conversion', () => {
  const metadata = stablecoinRatesMetadata([
    ['USDT', 0.9992],
    ['USDC', 1.0001],
    ['TRY', 50],
  ])
  assert.deepEqual(metadata, { stablecoin_usd_rates: { USDT: 0.9992, USDC: 1.0001 } })
  assert.equal(stablecoinRateFromMetadata(metadata, 'USDT'), 0.9992)
  assert.equal(stablecoinRateFromMetadata(metadata, 'USDC'), 1.0001)
  assert.equal(stablecoinRateFromMetadata(metadata, 'TRY'), 0)
})

test('historical stablecoin rate falls back to USD unit-price fields on transactional rows', () => {
  assert.equal(
    stablecoinRateFromTransaction(
      {
        transaction_type: 'BUY',
        target_asset: 'USDT',
        target_unit_price: 0.9985,
        metadata: {},
      },
      'USDT',
    ),
    0.9985,
  )
  assert.equal(
    stablecoinRateFromTransaction(
      {
        transaction_type: 'SELL',
        source_asset: 'USDC',
        source_unit_price: 1.0003,
        metadata: {},
      },
      'USDC',
    ),
    1.0003,
  )
  assert.equal(
    stablecoinRateFromTransaction(
      {
        transaction_type: 'OPENING',
        target_asset: 'USDT',
        target_unit_price: 48.5,
        metadata: {},
      },
      'USDT',
    ),
    0,
  )
})

test('stablecoin amount formatting does not rely on ISO-4217 currency mode', () => {
  assert.match(formatSettlementAmount(12.3456, 'USDT', 4), /12,3456 USDT/)
  assert.match(formatSettlementAmount(9.5, 'USDC', 2), /9,5 USDC/)
  assert.match(formatSettlementAmount(100, 'TRY', 2), /₺|TRY/)
})
