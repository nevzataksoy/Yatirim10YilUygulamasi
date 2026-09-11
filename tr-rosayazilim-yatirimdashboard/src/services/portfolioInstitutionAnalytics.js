import { ASSETS, buildPortfolioLedger } from './portfolioAnalytics.js'

export const UNASSIGNED_INSTITUTION_KEY = '__UNASSIGNED_INSTITUTION__'
export const POSITION_EPSILON = 0.0000000001

function normalizedName(value) {
  return String(value || '')
    .trim()
    .toLocaleLowerCase('tr-TR')
}

function institutionMeta(institution, fallbackName = '') {
  return {
    institutionId: institution?.id || null,
    name: institution?.name || fallbackName || 'Kurum Belirtilmemiş',
    institutionType: institution?.institution_type || 'OTHER',
    countryCode: institution?.country_code || null,
    isActive: institution?.is_active !== false,
  }
}

export function resolveTransactionInstitution(transaction, institutions = []) {
  const byId = new Map(
    (institutions || []).filter((item) => item?.id).map((item) => [item.id, item]),
  )
  const byName = new Map(
    (institutions || [])
      .filter((item) => normalizedName(item?.name))
      .map((item) => [normalizedName(item.name), item]),
  )

  const institutionId = transaction?.institution_id || null
  const platform = String(transaction?.platform || '').trim()

  if (institutionId) {
    const institution = byId.get(institutionId)
    return {
      key: `id:${institutionId}`,
      ...institutionMeta(institution, platform || 'Kurum'),
      institutionId,
      resolution: institution ? 'institution_id' : 'institution_id_without_dictionary',
      legacy: false,
      unassigned: false,
    }
  }

  if (platform) {
    const institution = byName.get(normalizedName(platform))
    if (institution) {
      return {
        key: `id:${institution.id}`,
        ...institutionMeta(institution, platform),
        resolution: 'platform_name_fallback',
        legacy: true,
        unassigned: false,
      }
    }

    return {
      key: `platform:${normalizedName(platform)}`,
      ...institutionMeta(null, platform),
      resolution: 'unmapped_platform',
      legacy: true,
      unassigned: false,
    }
  }

  return {
    key: UNASSIGNED_INSTITUTION_KEY,
    ...institutionMeta(null, 'Kurum Belirtilmemiş'),
    resolution: 'unassigned',
    legacy: true,
    unassigned: true,
  }
}

export function buildInstitutionLedgers(transactions = [], institutions = []) {
  const grouped = new Map()

  for (const transaction of transactions || []) {
    const resolved = resolveTransactionInstitution(transaction, institutions)
    let group = grouped.get(resolved.key)

    if (!group) {
      group = {
        ...resolved,
        transactions: [],
        resolutionSources: new Set(),
      }
      grouped.set(resolved.key, group)
    }

    group.transactions.push(transaction)
    group.resolutionSources.add(resolved.resolution)
    group.legacy = group.legacy || resolved.legacy
    group.unassigned = group.unassigned || resolved.unassigned
  }

  return [...grouped.values()].map((group) => ({
    key: group.key,
    institutionId: group.institutionId,
    name: group.name,
    institutionType: group.institutionType,
    countryCode: group.countryCode,
    isActive: group.isActive,
    legacy: group.legacy,
    unassigned: group.unassigned,
    resolutionSources: [...group.resolutionSources],
    transactionCount: group.transactions.length,
    transactions: group.transactions,
    ledger: buildPortfolioLedger(group.transactions),
  }))
}

export function positiveInstitutionAssets(ledger, epsilon = POSITION_EPSILON) {
  return ASSETS.map((asset) => ledger?.assets?.[asset])
    .filter(Boolean)
    .filter((item) => Number(item.quantity || 0) > epsilon)
}

export function valueInstitutionLedgerUsd(ledger, priceUsd) {
  const assets = positiveInstitutionAssets(ledger)
  let currentValueUsd = 0
  let costBasisUsd = 0
  let valuationComplete = true

  for (const item of assets) {
    costBasisUsd += Number(item.costBasisUsd || 0)
    const unitPriceUsd = item.asset === 'USD' ? 1 : Number(priceUsd?.(item.asset) || 0)
    if (!(unitPriceUsd > 0)) {
      valuationComplete = false
      continue
    }
    currentValueUsd += Number(item.quantity || 0) * unitPriceUsd
  }

  const realizedPnlUsd = Number(ledger?.realizedPnlUsd || 0)
  const unrealizedPnlUsd = valuationComplete ? currentValueUsd - costBasisUsd : null

  return {
    currentValueUsd: valuationComplete ? currentValueUsd : null,
    knownCurrentValueUsd: currentValueUsd,
    costBasisUsd,
    realizedPnlUsd,
    unrealizedPnlUsd,
    totalPnlUsd: unrealizedPnlUsd === null ? null : realizedPnlUsd + unrealizedPnlUsd,
    valuationComplete,
  }
}

export function buildInstitutionDistribution({ transactions = [], institutions = [], priceUsd } = {}) {
  const groups = buildInstitutionLedgers(transactions, institutions).map((group) => ({
    ...group,
    assets: positiveInstitutionAssets(group.ledger),
    valuation: valueInstitutionLedgerUsd(group.ledger, priceUsd),
  }))

  const valuationComplete = groups.every((group) => group.valuation.valuationComplete)
  const totalCurrentValueUsd = valuationComplete
    ? groups.reduce((sum, group) => sum + Number(group.valuation.currentValueUsd || 0), 0)
    : null

  return groups
    .map((group) => ({
      ...group,
      allocationPct:
        totalCurrentValueUsd !== null && totalCurrentValueUsd > 0
          ? (Number(group.valuation.currentValueUsd || 0) / totalCurrentValueUsd) * 100
          : null,
    }))
    .sort(
      (a, b) =>
        Number(b.valuation.currentValueUsd ?? b.valuation.knownCurrentValueUsd ?? 0) -
        Number(a.valuation.currentValueUsd ?? a.valuation.knownCurrentValueUsd ?? 0),
    )
}
