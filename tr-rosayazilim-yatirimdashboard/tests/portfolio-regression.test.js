import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPortfolioLedger } from '../src/services/portfolioAnalytics.js'
import {
  assertIdempotentTransactionMatch,
  assertTransactionRequestShape,
  effectiveTransactions,
  mergeUniqueTransactions,
  normalizeTransaction,
  replayTransactionBalances,
  transactionsForAccount,
} from '../src/services/portfolioTransactions.js'

const USER_ID = '10000000-0000-4000-8000-000000000001'
const ACCOUNT_ID = '20000000-0000-4000-8000-000000000001'
const SECOND_ACCOUNT_ID = '20000000-0000-4000-8000-000000000002'
const USD_TRY = 47.4

function closeTo(actual, expected, tolerance = 1e-8) {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `expected ${actual} to be within ${tolerance} of ${expected}`,
  )
}

function transaction(sequence, input, accountId = ACCOUNT_ID) {
  return normalizeTransaction(
    {
      id: `30000000-0000-4000-8000-${String(sequence).padStart(12, '0')}`,
      transaction_at: `2026-08-01T${String(sequence).padStart(2, '0')}:00:00.000Z`,
      price_currency: 'USD',
      fee_usd: 0,
      metadata: { regression_step: sequence },
      ...input,
    },
    USER_ID,
    accountId,
  )
}

function build100kTryScenario() {
  return [
    transaction(1, {
      transaction_type: 'CASH_IN',
      target_asset: 'TRY',
      target_quantity: 100000,
      gross_usd: 100000 / USD_TRY,
      net_usd: 100000 / USD_TRY,
    }),
    transaction(2, {
      transaction_type: 'BUY',
      source_asset: 'TRY',
      source_quantity: 24024,
      target_asset: 'BTC',
      target_quantity: 0.008,
      gross_usd: 24000 / USD_TRY,
      fee_usd: 24 / USD_TRY,
      net_usd: 24000 / USD_TRY,
    }),
    transaction(3, {
      transaction_type: 'BUY',
      source_asset: 'TRY',
      source_quantity: 22500,
      target_asset: 'ETH',
      target_quantity: 0.25,
      gross_usd: 22500 / USD_TRY,
      net_usd: 22500 / USD_TRY,
    }),
    transaction(4, {
      transaction_type: 'CONVERSION',
      source_asset: 'TRY',
      source_quantity: 12000,
      target_asset: 'USD',
      target_quantity: 12000 / USD_TRY,
      gross_usd: 12000 / USD_TRY,
      net_usd: 12000 / USD_TRY,
    }),
    transaction(5, {
      transaction_type: 'BUY',
      source_asset: 'USD',
      source_quantity: 189.189,
      target_asset: 'BTC',
      target_quantity: 0.003,
      gross_usd: 189,
      fee_usd: 0.189,
      net_usd: 189,
    }),
    transaction(6, {
      transaction_type: 'BUY',
      source_asset: 'TRY',
      source_quantity: 20660.64,
      target_asset: 'URA',
      target_quantity: 12,
      gross_usd: 20640 / USD_TRY,
      fee_usd: 20.64 / USD_TRY,
      net_usd: 20640 / USD_TRY,
    }),
    transaction(7, {
      transaction_type: 'CONVERSION',
      source_asset: 'ETH',
      source_quantity: 0.1,
      target_asset: 'BTC',
      target_quantity: 0.00294705,
      gross_usd: 192,
      fee_usd: 0.00000295 * 64800,
      net_usd: 192,
    }),
    transaction(8, {
      transaction_type: 'CONVERSION',
      source_asset: 'BTC',
      source_quantity: 0.004004,
      target_asset: 'ETH',
      target_quantity: 0.1352,
      gross_usd: 0.004 * 64800,
      fee_usd: 0.000004 * 64800,
      net_usd: 0.004 * 64800,
    }),
    transaction(9, {
      transaction_type: 'BUY',
      source_asset: 'TRY',
      source_quantity: 7040,
      target_asset: 'URA',
      target_quantity: 4,
      gross_usd: 7040 / USD_TRY,
      net_usd: 7040 / USD_TRY,
    }),
    transaction(10, {
      transaction_type: 'SELL',
      source_asset: 'URA',
      source_quantity: 6,
      target_asset: 'TRY',
      target_quantity: 11088.9,
      gross_usd: 11100 / USD_TRY,
      fee_usd: 11.1 / USD_TRY,
      net_usd: 11088.9 / USD_TRY,
    }),
    transaction(11, {
      transaction_type: 'SELL',
      source_asset: 'BTC',
      source_quantity: 0.002,
      target_asset: 'TRY',
      target_quantity: 6233.76,
      gross_usd: 6240 / USD_TRY,
      fee_usd: 6.24 / USD_TRY,
      net_usd: 6233.76 / USD_TRY,
    }),
    transaction(12, {
      transaction_type: 'CASH_OUT',
      source_asset: 'TRY',
      source_quantity: 25000,
      gross_usd: 25000 / USD_TRY,
      net_usd: 25000 / USD_TRY,
    }),
  ]
}

test('100,000 TRY scenario preserves every intermediate and final balance', () => {
  const rows = build100kTryScenario()
  const expectedBalances = [
    { TRY: 100000 },
    { TRY: 75976, BTC: 0.008 },
    { TRY: 53476, BTC: 0.008, ETH: 0.25 },
    { TRY: 41476, USD: 12000 / USD_TRY },
    { USD: 63.97555696202533, BTC: 0.011 },
    { TRY: 20815.36, URA: 12 },
    { ETH: 0.15, BTC: 0.01394705 },
    { ETH: 0.2852, BTC: 0.00994305 },
    { TRY: 13775.36, URA: 16 },
    { TRY: 24864.26, URA: 10 },
    { TRY: 31098.02, BTC: 0.00794305 },
    { TRY: 6098.02, USD: 63.97555696202533, BTC: 0.00794305, ETH: 0.2852, URA: 10 },
  ]

  rows.forEach(assertTransactionRequestShape)
  for (let index = 0; index < rows.length; index += 1) {
    const replay = replayTransactionBalances(rows.slice(0, index + 1))
    assert.equal(replay.valid, true)
    for (const [asset, expected] of Object.entries(expectedBalances[index])) {
      closeTo(replay.balances[asset], expected)
    }
  }
})

test('100,000 TRY ledger matches capital, fee and profit regression values', () => {
  const ledger = buildPortfolioLedger(build100kTryScenario())
  closeTo(ledger.assets.TRY.quantity, 6098.02)
  closeTo(ledger.assets.USD.quantity, 63.97555696202533)
  closeTo(ledger.assets.BTC.quantity, 0.00794305)
  closeTo(ledger.assets.ETH.quantity, 0.2852)
  closeTo(ledger.assets.URA.quantity, 10)
  closeTo(ledger.netContributedUsd, 1582.2784810126582)
  closeTo(ledger.realizedPnlUsd, 19.26901860603975)
  closeTo(ledger.totalFeesUsd, 1.946954936708861)

  const prices = { TRY: 1 / USD_TRY, USD: 1, BTC: 64800, ETH: 1920, URA: 37.5 }
  const marketValue = Object.values(ledger.assets).reduce(
    (sum, asset) => sum + asset.quantity * prices[asset.asset],
    0,
  )
  const remainingBasis = Object.values(ledger.assets).reduce(
    (sum, asset) => sum + asset.costBasisUsd,
    0,
  )
  const unrealizedPnl = marketValue - remainingBasis
  const totalPnl = unrealizedPnl + ledger.realizedPnlUsd

  closeTo(marketValue, 1629.919408, 1e-6)
  closeTo(unrealizedPnl, 28.371908, 1e-6)
  closeTo(totalPnl, 47.640927, 1e-6)
})

test('chronological replay is deterministic and rejects an overdraft', () => {
  const rows = build100kTryScenario()
  const shuffled = [
    rows[11],
    rows[3],
    rows[8],
    ...rows.slice(0, 3),
    ...rows.slice(4, 8),
    ...rows.slice(9, 11),
  ]
  assert.deepEqual(buildPortfolioLedger(shuffled), buildPortfolioLedger(rows))
  assert.deepEqual(replayTransactionBalances(shuffled), replayTransactionBalances(rows))

  const invalid = transaction(13, {
    transaction_type: 'CASH_OUT',
    source_asset: 'TRY',
    source_quantity: 7000,
    gross_usd: 7000 / USD_TRY,
    net_usd: 7000 / USD_TRY,
  })
  const replay = replayTransactionBalances([...rows, invalid])
  assert.equal(replay.valid, false)
  assert.equal(replay.asset, 'TRY')
  closeTo(replay.available, 6098.02)
})

test('account filtering prevents one portfolio ledger from consuming another account', () => {
  const primaryRows = build100kTryScenario()
  const secondaryRows = [
    transaction(
      20,
      {
        transaction_type: 'CASH_IN',
        target_asset: 'TRY',
        target_quantity: 5000,
        gross_usd: 5000 / USD_TRY,
        net_usd: 5000 / USD_TRY,
      },
      SECOND_ACCOUNT_ID,
    ),
  ]
  const allRows = [...secondaryRows, ...primaryRows]

  assert.equal(transactionsForAccount(allRows, ACCOUNT_ID).length, 12)
  assert.equal(transactionsForAccount(allRows, SECOND_ACCOUNT_ID).length, 1)
  closeTo(
    buildPortfolioLedger(transactionsForAccount(allRows, ACCOUNT_ID)).assets.TRY.quantity,
    6098.02,
  )
  closeTo(
    buildPortfolioLedger(transactionsForAccount(allRows, SECOND_ACCOUNT_ID)).assets.TRY.quantity,
    5000,
  )
})

test('append-only revision and cancellation leave only the effective chain tip in the ledger', () => {
  const cashIn = transaction(30, {
    transaction_type: 'CASH_IN',
    target_asset: 'TRY',
    target_quantity: 10000,
    gross_usd: 10000 / USD_TRY,
    net_usd: 10000 / USD_TRY,
  })
  const buy = transaction(31, {
    transaction_type: 'BUY',
    source_asset: 'TRY',
    source_quantity: 3000,
    target_asset: 'BTC',
    target_quantity: 0.001,
    gross_usd: 3000 / USD_TRY,
    net_usd: 3000 / USD_TRY,
  })
  const revision = transaction(32, {
    ...buy,
    id: '30000000-0000-4000-8000-000000000032',
    source_quantity: 2500,
    target_quantity: 0.001,
    gross_usd: 2500 / USD_TRY,
    net_usd: 2500 / USD_TRY,
    metadata: {
      revision_root_id: buy.id,
      revision_number: 2,
      supersedes_transaction_id: buy.id,
    },
  })
  const cancellation = transaction(33, {
    ...revision,
    id: '30000000-0000-4000-8000-000000000033',
    source_quantity: null,
    target_quantity: null,
    gross_usd: 0,
    fee_usd: 0,
    net_usd: 0,
    metadata: {
      ...revision.metadata,
      revision_number: 3,
      supersedes_transaction_id: revision.id,
      cancelled_at: '2026-08-01T23:00:00.000Z',
    },
  })

  const revisedLedger = buildPortfolioLedger(effectiveTransactions([cashIn, buy, revision]))
  closeTo(revisedLedger.assets.TRY.quantity, 7500)
  closeTo(revisedLedger.assets.BTC.quantity, 0.001)

  const cancelledLedger = buildPortfolioLedger(
    effectiveTransactions([cashIn, buy, revision, cancellation]),
  )
  closeTo(cancelledLedger.assets.TRY.quantity, 10000)
  closeTo(cancelledLedger.assets.BTC.quantity, 0)
})

test('stable request IDs make retries idempotent and reject ID reuse with different content', () => {
  const [request] = build100kTryScenario()
  const serverRow = {
    ...request,
    target_quantity: '100000.000000000000',
    gross_usd: request.gross_usd.toFixed(8),
    fee_usd: '0.00000000',
    net_usd: request.net_usd.toFixed(8),
  }

  assert.doesNotThrow(() => assertIdempotentTransactionMatch(serverRow, request))
  assert.equal(mergeUniqueTransactions([serverRow], [request]).length, 1)

  const changedRetry = { ...request, target_quantity: 99999 }
  assert.throws(
    () => assertIdempotentTransactionMatch(serverRow, changedRetry),
    /daha önce farklı içerikle kullanılmış/,
  )
})
