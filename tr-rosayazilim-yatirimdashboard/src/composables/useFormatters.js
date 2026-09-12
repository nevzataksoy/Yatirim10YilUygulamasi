export function useFormatters() {
  const usd = new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  })

  const tryMoney = new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
    maximumFractionDigits: 2,
  })

  function formatUsd(value) {
    return usd.format(Number(value || 0))
  }

  function formatTry(value) {
    return tryMoney.format(Number(value || 0))
  }

  function formatNumber(value, digits = 8) {
    return new Intl.NumberFormat('tr-TR', { maximumFractionDigits: digits }).format(
      Number(value || 0),
    )
  }

  function formatDate(value) {
    if (!value) return '—'
    return new Intl.DateTimeFormat('tr-TR', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value))
  }

  return { formatUsd, formatTry, formatNumber, formatDate }
}
