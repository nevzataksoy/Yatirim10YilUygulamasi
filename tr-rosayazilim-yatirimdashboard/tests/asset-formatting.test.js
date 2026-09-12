import assert from 'node:assert/strict'
import test from 'node:test'
import {
  assetQuantityDigits,
  formatAssetQuantity,
  formatSignedAssetQuantity,
  formatAssetUnitPrice,
} from '../src/services/assetFormatting.js'

test('asset quantity precision follows real-world display contract', () => {
  assert.equal(assetQuantityDigits('BTC'), 8)
  assert.equal(assetQuantityDigits('ETH'), 6)
  assert.equal(assetQuantityDigits('URA'), 4)
  assert.equal(assetQuantityDigits('USDT'), 6)
  assert.equal(assetQuantityDigits('USDC'), 6)
  assert.equal(assetQuantityDigits('TRY'), 2)
})

test('TRY and USD quantities use monetary separators instead of crypto precision', () => {
  const tryValue = formatAssetQuantity(5000, 'TRY')
  const usdValue = formatAssetQuantity(104.23, 'USD')

  assert.match(tryValue, /5\.000,00/)
  assert.ok(tryValue.includes('₺') || tryValue.includes('TRY'))
  assert.match(usdValue, /104,23/)
  assert.ok(usdValue.includes('$') || usdValue.includes('USD'))
})

test('crypto and stablecoin quantities do not force meaningless trailing zeros', () => {
  assert.equal(formatAssetQuantity(0.12345678, 'BTC'), '0,12345678 BTC')
  assert.equal(formatAssetQuantity(1.234567, 'ETH'), '1,234567 ETH')
  assert.equal(formatAssetQuantity(12.3456, 'URA'), '12,3456 URA')
  assert.equal(formatAssetQuantity(100, 'USDT'), '100 USDT')
  assert.equal(formatAssetQuantity(100.1234567, 'USDC'), '100,123457 USDC')
})

test('signed and unit-price formatting preserve the asset convention', () => {
  assert.equal(formatSignedAssetQuantity(1.25, 'USDT'), '+1,25 USDT')
  assert.equal(formatSignedAssetQuantity(-0.001, 'BTC'), '-0,001 BTC')
  assert.match(formatAssetUnitPrice(3_154_250.25, 'TRY'), /3\.154\.250,25/)
  assert.equal(formatAssetUnitPrice(64_912.45, 'USDT'), '64.912,45 USDT')
})
