import Decimal from 'decimal.js'

export const ASSETS = ['BTC', 'ETH', 'URA', 'USD', 'TRY']
const EPSILON = new Decimal('0.000000000001')

function amount(value) {
  return new Decimal(value || 0)
}

export function buildPortfolioLedger(transactions) {
  const state = Object.fromEntries(
    ASSETS.map((asset) => [
      asset,
      { qty: new Decimal(0), basis: new Decimal(0), realized: new Decimal(0) },
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

  const rows = [...transactions].sort(
    (a, b) => new Date(a.transaction_at).getTime() - new Date(b.transaction_at).getTime(),
  )

  function removeBasis(asset, quantity) {
    const item = state[asset]
    if (!item || quantity.lte(0) || item.qty.lte(EPSILON)) return new Decimal(0)
    const actual = Decimal.min(quantity, item.qty)
    const unitBasis = item.basis.div(item.qty)
    const removed = unitBasis.mul(actual)
    item.qty = item.qty.minus(actual)
    item.basis = Decimal.max(0, item.basis.minus(removed))
    if (item.qty.abs().lte(EPSILON)) {
      item.qty = new Decimal(0)
      item.basis = new Decimal(0)
    }
    return removed
  }

  function addPosition(asset, quantity, basisUsd) {
    const item = state[asset]
    if (!item || quantity.lte(0)) return
    item.qty = item.qty.plus(quantity)
    item.basis = item.basis.plus(Decimal.max(0, basisUsd))
  }

  for (const tx of rows) {
    const fee = amount(tx.fee_usd)
    const gross = amount(tx.gross_usd)
    const net =
      tx.net_usd === null || tx.net_usd === undefined
        ? Decimal.max(0, gross.minus(fee))
        : amount(tx.net_usd)
    totalFeesUsd = totalFeesUsd.plus(fee)

    if (tx.transaction_type === 'OPENING' && tx.target_asset && tx.target_quantity) {
      const basis = gross.plus(fee)
      addPosition(tx.target_asset, amount(tx.target_quantity), basis)
      openingCapitalUsd = openingCapitalUsd.plus(basis)
      netContributedUsd = netContributedUsd.plus(basis)
      continue
    }

    if (tx.transaction_type === 'BUY' && tx.target_asset && tx.target_quantity) {
      buyVolumeUsd = buyVolumeUsd.plus(gross)

      if (tx.source_asset && tx.source_quantity) {
        // source_quantity gerçek hesap düşüşüdür. Komisyon kaynak varlıktan kesildiyse
        // bu miktara zaten dahildir; maliyet bazına ikinci kez fee eklenmez.
        const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
        addPosition(tx.target_asset, amount(tx.target_quantity), removed)
      } else {
        // Eski BUY kayıtları kaynak bakiyesi tutmadığı için harici fonlama olarak korunur.
        const basis = gross.plus(fee)
        addPosition(tx.target_asset, amount(tx.target_quantity), basis)
        netContributedUsd = netContributedUsd.plus(basis)
      }
      continue
    }

    if (tx.transaction_type === 'CASH_IN' && tx.target_asset && tx.target_quantity) {
      const basis = gross.gt(0) ? gross : amount(tx.target_quantity)
      addPosition(tx.target_asset, amount(tx.target_quantity), basis)
      cashInUsd = cashInUsd.plus(gross)
      netContributedUsd = netContributedUsd.plus(gross)
      continue
    }

    if (tx.transaction_type === 'CASH_OUT' && tx.source_asset && tx.source_quantity) {
      removeBasis(tx.source_asset, amount(tx.source_quantity))
      cashOutUsd = cashOutUsd.plus(gross)
      netContributedUsd = netContributedUsd.minus(gross)
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
      addPosition(tx.target_asset, amount(tx.target_quantity), removed)
      conversionVolumeUsd = conversionVolumeUsd.plus(gross)
      continue
    }

    if (
      (tx.transaction_type === 'SELL' || tx.transaction_type === 'EXIT') &&
      tx.source_asset &&
      tx.source_quantity
    ) {
      const removed = removeBasis(tx.source_asset, amount(tx.source_quantity))
      const pnl = net.minus(removed)
      state[tx.source_asset].realized = state[tx.source_asset].realized.plus(pnl)
      realizedPnlUsd = realizedPnlUsd.plus(pnl)
      if (tx.target_asset && tx.target_quantity)
        addPosition(tx.target_asset, amount(tx.target_quantity), net)
    }
  }

  const assets = Object.fromEntries(
    ASSETS.map((asset) => {
      const item = state[asset]
      const quantity = item.qty.toNumber()
      const costBasisUsd = item.basis.toNumber()
      return [
        asset,
        {
          asset,
          quantity,
          costBasisUsd,
          averageCostUsd: quantity > 0 ? item.basis.div(item.qty).toNumber() : 0,
          realizedPnlUsd: item.realized.toNumber(),
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
  }
}
