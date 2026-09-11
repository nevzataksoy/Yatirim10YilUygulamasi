import Decimal from 'decimal.js'
import { stablecoinRateFromMetadata } from './transactionCurrency.js'

export const INVESTMENT_ASSETS = Object.freeze(['BTC', 'ETH', 'URA'])
export const SETTLEMENT_ASSETS = Object.freeze(['USD', 'TRY', 'USDT', 'USDC'])
export const ASSETS = Object.freeze([...INVESTMENT_ASSETS, ...SETTLEMENT_ASSETS])
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
    const rate = amount(stablecoinRateFromMetadata(tx?.metadata, asset))
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
        // source_quantity gerçek hesap düşüşüdür. Komisyon kaynak varlıktan kesildiyse
        // bu miktara zaten dahildir; maliyet bazına ikinci kez fee eklenmez.
        const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
        addPosition(tx.target_asset, amount(tx.target_quantity), removed.usd, removed.historical)
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
      removeBasis(tx.source_asset, amount(tx.source_quantity))
      cashOutUsd = cashOutUsd.plus(gross)
      netContributedUsd = netContributedUsd.minus(gross)
      const historicalGross = historicalValuesFromUsd(tx, gross)
      mergeHistoricalValues(historicalMetrics.cashOut, historicalGross)
      mergeHistoricalValues(historicalMetrics.netContributed, historicalGross, -1)
      continue
    }

    if (
      tx.transaction_type === 'CONVERSION' &&
      tx.source_asset &&
      tx.target_asset &&
      tx.source_quantity &&
      tx.target_quantity
    ) {
      // Her iki miktar da gerçek hesap bakiyesi değişimini temsil eder. Hedef komisyonu
      // target_quantity'nin netleşmesiyle, kaynak komisyonu source_quantity artışıyla yansır.
      const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
      addPosition(tx.target_asset, amount(tx.target_quantity), removed.usd, removed.historical)
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
      const pnlHistorical = emptyHistoricalValues()

      for (const settlementAsset of SETTLEMENT_ASSETS) {
        pnlHistorical[settlementAsset].value = proceedsHistorical[settlementAsset].value.minus(
          removed.historical[settlementAsset].value,
        )
        pnlHistorical[settlementAsset].complete =
          proceedsHistorical[settlementAsset].complete &&
          removed.historical[settlementAsset].complete
      }

      state[tx.source_asset].realized = state[tx.source_asset].realized.plus(pnl)
      mergeHistoricalValues(state[tx.source_asset].realizedHistorical, pnlHistorical)
      realizedPnlUsd = realizedPnlUsd.plus(pnl)
      mergeHistoricalValues(historicalMetrics.realizedPnl, pnlHistorical)

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
