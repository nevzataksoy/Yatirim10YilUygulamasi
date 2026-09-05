import assert from 'node:assert/strict'
import test from 'node:test'
import {
  convertUsdWithQuotes,
  priceUsdForAsset,
} from '../src/services/display-quotes/conversion.js'
import {
  parseCoinbaseSpot,
  parseCoinbaseUsdFx,
  parseFawazUsdFx,
  parseFrankfurterUsdFx,
  parseYahooChart,
} from '../src/services/display-quotes/quoteParsers.js'

const quotes = {
  BTC_USD: { value: 100_000 },
  ETH_USD: { value: 4_000 },
  URA_USD: { value: 45 },
  USD_TRY: { value: 44 },
  EUR_USD: { value: 1.1 },
}

test('USD display conversion uses canonical quote directions', () => {
  assert.equal(convertUsdWithQuotes(100, 'USD', quotes), 100)
  assert.equal(convertUsdWithQuotes(100, 'TRY', quotes), 4_400)
  assert.ok(Math.abs(convertUsdWithQuotes(110, 'EUR', quotes) - 100) < 1e-12)
  assert.equal(convertUsdWithQuotes(100_000, 'BTC', quotes), 1)
  assert.equal(convertUsdWithQuotes(8_000, 'ETH', quotes), 2)
})

test('priceUsdForAsset derives TRY USD price and reads canonical assets', () => {
  assert.equal(priceUsdForAsset(quotes, 'TRY'), 1 / 44)
  assert.equal(priceUsdForAsset(quotes, 'EUR'), 1.1)
  assert.equal(priceUsdForAsset(quotes, 'URA'), 45)
})

test('Coinbase parsers normalize spot and inverse EUR direction', () => {
  assert.equal(parseCoinbaseSpot({ data: { amount: '101234.56' } }), 101234.56)
  const fx = parseCoinbaseUsdFx({ data: { rates: { TRY: '44', EUR: '0.9090909091' } } })
  assert.equal(fx.USD_TRY, 44)
  assert.ok(Math.abs(fx.EUR_USD - 1.1) < 1e-9)
  const partialFx = parseCoinbaseUsdFx({ data: { rates: { TRY: '44' } } })
  assert.deepEqual(partialFx, { USD_TRY: 44 })
})

test('Yahoo parser exposes regular market price and timestamp', () => {
  const parsed = parseYahooChart({
    chart: { result: [{ meta: { regularMarketPrice: 46.25, regularMarketTime: 1_700_000_000 } }] },
  })
  assert.equal(parsed.value, 46.25)
  assert.equal(parsed.marketAt, new Date(1_700_000_000 * 1000).toISOString())
})

test('Frankfurter v2 and Fawaz parsers normalize USD/TRY and EUR/USD', () => {
  const frankfurter = parseFrankfurterUsdFx([
    { date: '2026-08-21', base: 'USD', quote: 'TRY', rate: 44 },
    { date: '2026-08-21', base: 'USD', quote: 'EUR', rate: 0.91 },
  ])
  assert.equal(frankfurter.USD_TRY.value, 44)
  assert.ok(Math.abs(frankfurter.EUR_USD.value - 1 / 0.91) < 1e-12)

  const fawaz = parseFawazUsdFx({ date: '2026-08-21', usd: { try: 44.1, eur: 0.9 } })
  assert.equal(fawaz.USD_TRY.value, 44.1)
  assert.ok(Math.abs(fawaz.EUR_USD.value - 1 / 0.9) < 1e-12)
})
