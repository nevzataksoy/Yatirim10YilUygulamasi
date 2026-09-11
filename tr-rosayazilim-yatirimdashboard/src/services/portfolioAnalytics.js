import Decimal from 'decimal.js'
import { stablecoinRateFromTransaction } from './transactionCurrency.js'

export const TRADEABLE_ASSETS = Object.freeze(['BTC', 'ETH', 'URA', 'USDT', 'USDC'])
// Geriye dönük import uyumluluğu; yeni kod TRADEABLE_ASSETS kullanmalı.
export const INVESTMENT_ASSETS = TRADEABLE_ASSETS
export const SETTLEMENT_ASSETS = Object.freeze(['USD', 'TRY', 'USDT', 'USDC'])
export const ASSETS = Object.freeze([...new Set([...TRADEABLE_ASSETS, ...SETTLEMENT_ASSETS])])
const EPSILON = new Decimal('0.000000000001')

function amount(value) {
  return new Decimal(value || 0)
}

function emptyHistoricalValues() {
  return Object.fromEntries(
    SETTLEMENT_ASSETS.map((asset) => [
      asset,
      { value: new Decimal(0), complete: true },
    ]),
  )
}

function historicalValuesFromUsd(tx, usdValue) {
  const usd = amount(usdValue)
  const values = emptyHistoricalValues()
  values.USD.value = usd

  if (usd.eq(0)) return values

  const usdTry = amount(tx?.usd_try)
  if (usdTry.gt(0)) values.TRY.value = usd.mul(usdTry)
  else values.TRY.complete = false

  for (const asset of ['USDT', 'USDC']) {
    const rate = amount(stablecoinRateFromTransaction(tx, asset))
    if (rate.gt(0)) values[asset].value = usd.div(rate)
    else values[asset].complete = false
  }

  return values
}

function cloneHistoricalValues(source) {
  return Object.fromEntries(
    SETTLEMENT_ASSETS.map((asset) => [
      asset,
      {
        value: new Decimal(source?.[asset]?.value || 0),
        complete: source?.[asset]?.complete !== false,
      },
    ]),
  )
}

function mergeHistoricalValues(target, incoming, sign = 1) {
  for (const asset of SETTLEMENT_ASSETS) {
    target[asset].value = target[asset].value.plus(incoming[asset].value.mul(sign))
    target[asset].complete = target[asset].complete && incoming[asset].complete
  }
}

function subtractHistoricalValues(left, right) {
  const result = emptyHistoricalValues()
  for (const asset of SETTLEMENT_ASSETS) {
    result[asset].value = left[asset].value.minus(right[asset].value)
    result[asset].complete = left[asset].complete && right[asset].complete
  }
  return result
}

function historicalValuesToNumbers(values) {
  return Object.fromEntries(
    SETTLEMENT_ASSETS.map((asset) => [
      asset,
      values[asset].complete ? values[asset].value.toNumber() : null,
    ]),
  )
}

export function buildPortfolioLedger(transactions) {
  const state = Object.fromEntries(
    ASSETS.map((asset) => [
      asset,
      {
        qty: new Decimal(0),
        basis: new Decimal(0),
        historicalBasis: emptyHistoricalValues(),
        realized: new Decimal(0),
        realizedHistorical: emptyHistoricalValues(),
      },
    ]),
  )
  let netContributedUsd = new Decimal(0)
  let openingCapitalUsd = new Decimal(0)
  let cashInUsd = new Decimal(0)
  let cashOutUsd = new Decimal(0)
  let buyVolumeUsd = new Decimal(0)
  let conversionVolumeUsd = new Decimal(0)
  let totalFeesUsd = new Decimal(0)
  let realizedPnlUsd = new Decimal(0)

  const historicalMetrics = {
    netContributed: emptyHistoricalValues(),
    openingCapital: emptyHistoricalValues(),
    cashIn: emptyHistoricalValues(),
    cashOut: emptyHistoricalValues(),
    buyVolume: emptyHistoricalValues(),
    conversionVolume: emptyHistoricalValues(),
    totalFees: emptyHistoricalValues(),
    realizedPnl: emptyHistoricalValues(),
  }

  const rows = [...transactions].sort(
    (a, b) => new Date(a.transaction_at).getTime() - new Date(b.transaction_at).getTime(),
  )

  function removeBasis(asset, quantity) {
    const item = state[asset]
    if (!item || quantity.lte(0) || item.qty.lte(EPSILON)) {
      return { usd: new Decimal(0), historical: emptyHistoricalValues() }
    }

    const beforeQty = item.qty
    const actual = Decimal.min(quantity, beforeQty)
    const ratio = actual.div(beforeQty)
    const removedUsd = item.basis.mul(ratio)
    const removedHistorical = emptyHistoricalValues()

    for (const settlementAsset of SETTLEMENT_ASSETS) {
      removedHistorical[settlementAsset].value = item.historicalBasis[settlementAsset].value.mul(ratio)
      removedHistorical[settlementAsset].complete = item.historicalBasis[settlementAsset].complete
      item.historicalBasis[settlementAsset].value = item.historicalBasis[settlementAsset].value.minus(
        removedHistorical[settlementAsset].value,
      )
    }

    item.qty = item.qty.minus(actual)
    item.basis = Decimal.max(0, item.basis.minus(removedUsd))
    if (item.qty.abs().lte(EPSILON)) {
      item.qty = new Decimal(0)
      item.basis = new Decimal(0)
      item.historicalBasis = emptyHistoricalValues()
    }

    return { usd: removedUsd, historical: removedHistorical }
  }

  function addPosition(asset, quantity, basisUsd, historicalBasis) {
    const item = state[asset]
    if (!item || quantity.lte(0)) return

    const hadPosition = item.qty.gt(EPSILON)
    item.qty = item.qty.plus(quantity)
    item.basis = item.basis.plus(Decimal.max(0, basisUsd))

    if (!hadPosition) item.historicalBasis = cloneHistoricalValues(historicalBasis)
    else mergeHistoricalValues(item.historicalBasis, historicalBasis)
  }

  function recordRealized(asset, pnlUsd, pnlHistorical) {
    if (!state[asset]) return
    state[asset].realized = state[asset].realized.plus(pnlUsd)
    mergeHistoricalValues(state[asset].realizedHistorical, pnlHistorical)
    realizedPnlUsd = realizedPnlUsd.plus(pnlUsd)
    mergeHistoricalValues(historicalMetrics.realizedPnl, pnlHistorical)
  }

  for (const tx of rows) {
    const fee = amount(tx.fee_usd)
    const gross = amount(tx.gross_usd)
    const net =
      tx.net_usd === null || tx.net_usd === undefined
        ? Decimal.max(0, gross.minus(fee))
        : amount(tx.net_usd)
    const feeHistorical = historicalValuesFromUsd(tx, fee)
    totalFeesUsd = totalFeesUsd.plus(fee)
    mergeHistoricalValues(historicalMetrics.totalFees, feeHistorical)

    if (tx.transaction_type === 'OPENING' && tx.target_asset && tx.target_quantity) {
      const basis = gross.plus(fee)
      const historicalBasis = historicalValuesFromUsd(tx, basis)
      addPosition(tx.target_asset, amount(tx.target_quantity), basis, historicalBasis)
      openingCapitalUsd = openingCapitalUsd.plus(basis)
      netContributedUsd = netContributedUsd.plus(basis)
      mergeHistoricalValues(historicalMetrics.openingCapital, historicalBasis)
      mergeHistoricalValues(historicalMetrics.netContributed, historicalBasis)
      continue
    }

    if (tx.transaction_type === 'BUY' && tx.target_asset && tx.target_quantity) {
      buyVolumeUsd = buyVolumeUsd.plus(gross)
      mergeHistoricalValues(historicalMetrics.buyVolume, historicalValuesFromUsd(tx, gross))

      if (tx.source_asset && tx.source_quantity) {
        const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
        const acquisitionBasisUsd = gross.plus(fee)
        const acquisitionHistorical = historicalValuesFromUsd(tx, acquisitionBasisUsd)
        const sourcePnl = acquisitionBasisUsd.minus(removed.usd)
        const sourcePnlHistorical = subtractHistoricalValues(acquisitionHistorical, removed.historical)
        recordRealized(tx.source_asset, sourcePnl, sourcePnlHistorical)
        addPosition(
          tx.target_asset,
          amount(tx.target_quantity),
          acquisitionBasisUsd,
          acquisitionHistorical,
        )
      } else {
        // Eski BUY kayıtları kaynak bakiyesi tutmadığı için harici fonlama olarak korunur.
        const basis = gross.plus(fee)
        const historicalBasis = historicalValuesFromUsd(tx, basis)
        addPosition(tx.target_asset, amount(tx.target_quantity), basis, historicalBasis)
        netContributedUsd = netContributedUsd.plus(basis)
        mergeHistoricalValues(historicalMetrics.netContributed, historicalBasis)
      }
      continue
    }

    if (tx.transaction_type === 'CASH_IN' && tx.target_asset && tx.target_quantity) {
      const basis = gross.gt(0) ? gross : amount(tx.target_quantity)
      const historicalBasis = historicalValuesFromUsd(tx, basis)
      addPosition(tx.target_asset, amount(tx.target_quantity), basis, historicalBasis)
      cashInUsd = cashInUsd.plus(gross)
      netContributedUsd = netContributedUsd.plus(gross)
      mergeHistoricalValues(historicalMetrics.cashIn, historicalValuesFromUsd(tx, gross))
      mergeHistoricalValues(historicalMetrics.netContributed, historicalValuesFromUsd(tx, gross))
      continue
    }

    if (tx.transaction_type === 'CASH_OUT' && tx.source_asset && tx.source_quantity) {
      const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
      const withdrawalHistorical = historicalValuesFromUsd(tx, gross)
      const pnl = gross.minus(removed.usd)
      const pnlHistorical = subtractHistoricalValues(withdrawalHistorical, removed.historical)
      recordRealized(tx.source_asset, pnl, pnlHistorical)
      cashOutUsd = cashOutUsd.plus(gross)
      netContributedUsd = netContributedUsd.minus(gross)
      mergeHistoricalValues(historicalMetrics.cashOut, withdrawalHistorical)
      mergeHistoricalValues(historicalMetrics.netContributed, withdrawalHistorical, -1)
      continue
    }

    if (
      tx.transaction_type === 'CONVERSION' &&
      tx.source_asset &&
      tx.target_asset &&
      tx.source_quantity &&
      tx.target_quantity
    ) {
      const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
      const targetUnitPriceUsd = amount(tx.target_unit_price)
      const targetQuantity = amount(tx.target_quantity)
      const targetBasisUsd =
        targetUnitPriceUsd.gt(0) && targetQuantity.gt(0)
          ? targetUnitPriceUsd.mul(targetQuantity)
          : gross
      const targetHistorical = historicalValuesFromUsd(tx, targetBasisUsd)
      const sourcePnl = targetBasisUsd.minus(removed.usd)
      const sourcePnlHistorical = subtractHistoricalValues(targetHistorical, removed.historical)
      recordRealized(tx.source_asset, sourcePnl, sourcePnlHistorical)
      addPosition(tx.target_asset, targetQuantity, targetBasisUsd, targetHistorical)
      conversionVolumeUsd = conversionVolumeUsd.plus(gross)
      mergeHistoricalValues(
        historicalMetrics.conversionVolume,
        historicalValuesFromUsd(tx, gross),
      )
      continue
    }

    if (
      (tx.transaction_type === 'SELL' || tx.transaction_type === 'EXIT') &&
      tx.source_asset &&
      tx.source_quantity
    ) {
      const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
      const pnl = net.minus(removed.usd)
      const proceedsHistorical = historicalValuesFromUsd(tx, net)
      const pnlHistorical = subtractHistoricalValues(proceedsHistorical, removed.historical)
      recordRealized(tx.source_asset, pnl, pnlHistorical)

      if (tx.target_asset && tx.target_quantity) {
        addPosition(tx.target_asset, amount(tx.target_quantity), net, proceedsHistorical)
      }
    }
  }

  const assets = Object.fromEntries(
    ASSETS.map((asset) => {
      const item = state[asset]
      const quantity = item.qty.toNumber()
      const costBasisUsd = item.basis.toNumber()
      const historicalCostBasis = historicalValuesToNumbers(item.historicalBasis)
      const historicalAverageCost = Object.fromEntries(
        SETTLEMENT_ASSETS.map((settlementAsset) => [
          settlementAsset,
          quantity > 0 && historicalCostBasis[settlementAsset] !== null
            ? historicalCostBasis[settlementAsset] / quantity
            : quantity > 0
              ? null
              : 0,
        ]),
      )

      return [
        asset,
        {
          asset,
          quantity,
          costBasisUsd,
          averageCostUsd: quantity > 0 ? item.basis.div(item.qty).toNumber() : 0,
          historicalCostBasis,
          historicalAverageCost,
          realizedPnlUsd: item.realized.toNumber(),
          realizedPnlHistorical: historicalValuesToNumbers(item.realizedHistorical),
        },
      ]
    }),
  )

  return {
    assets,
    netContributedUsd: netContributedUsd.toNumber(),
    openingCapitalUsd: openingCapitalUsd.toNumber(),
    cashInUsd: cashInUsd.toNumber(),
    cashOutUsd: cashOutUsd.toNumber(),
    buyVolumeUsd: buyVolumeUsd.toNumber(),
    conversionVolumeUsd: conversionVolumeUsd.toNumber(),
    totalFeesUsd: totalFeesUsd.toNumber(),
    realizedPnlUsd: realizedPnlUsd.toNumber(),
    historical: {
      netContributed: historicalValuesToNumbers(historicalMetrics.netContributed),
      openingCapital: historicalValuesToNumbers(historicalMetrics.openingCapital),
      cashIn: historicalValuesToNumbers(historicalMetrics.cashIn),
      cashOut: historicalValuesToNumbers(historicalMetrics.cashOut),
      buyVolume: historicalValuesToNumbers(historicalMetrics.buyVolume),
      conversionVolume: historicalValuesToNumbers(historicalMetrics.conversionVolume),
      totalFees: historicalValuesToNumbers(historicalMetrics.totalFees),
      realizedPnl: historicalValuesToNumbers(historicalMetrics.realizedPnl),
    },
  }
}
