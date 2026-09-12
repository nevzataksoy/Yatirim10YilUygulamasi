import { DISPLAY_QUOTE_BACKOFF_MS, DISPLAY_QUOTE_REFRESH_MS } from './quoteConfig.js'
import {
  fetchCryptoDisplayQuotes,
  fetchFxDisplayQuotes,
  fetchUraDisplayQuote,
} from './displayQuoteService.js'

let activeScheduler = null

const GROUP_CONFIG = Object.freeze({
  crypto: {
    interval: DISPLAY_QUOTE_REFRESH_MS.crypto,
    snapshotKeys: ['BTC_USD', 'ETH_USD'],
    fetcher: fetchCryptoDisplayQuotes,
  },
  fx: {
    interval: DISPLAY_QUOTE_REFRESH_MS.slow,
    snapshotKeys: ['USD_TRY', 'EUR_USD'],
    fetcher: fetchFxDisplayQuotes,
  },
  ura: {
    interval: DISPLAY_QUOTE_REFRESH_MS.slow,
    snapshotKeys: ['URA_USD'],
    fetcher: fetchUraDisplayQuote,
  },
})

function delayFor(group, failures) {
  if (!failures) return GROUP_CONFIG[group].interval
  return DISPLAY_QUOTE_BACKOFF_MS[Math.min(failures - 1, DISPLAY_QUOTE_BACKOFF_MS.length - 1)]
}

export function createDisplayQuoteScheduler({ quoteStore, engineStore }) {
  const groups = Object.keys(GROUP_CONFIG)
  const timers = Object.fromEntries(groups.map((group) => [group, null]))
  const inFlight = Object.fromEntries(groups.map((group) => [group, null]))
  const failures = Object.fromEntries(groups.map((group) => [group, 0]))
  let active = false

  function clearTimer(group) {
    if (timers[group]) clearTimeout(timers[group])
    timers[group] = null
  }

  function schedule(group) {
    clearTimer(group)
    if (!active) return
    timers[group] = setTimeout(() => runGroup(group), delayFor(group, failures[group]))
  }

  async function runGroup(group, { force = false } = {}) {
    if (!GROUP_CONFIG[group]) throw new Error(`Bilinmeyen display quote grubu: ${group}`)
    if (!active && !force) return null
    if (inFlight[group]) return inFlight[group]

    const config = GROUP_CONFIG[group]
    const execute = async () => {
      const result = await config.fetcher()
      quoteStore.applyQuotes(result.quotes)
      quoteStore.setProviderErrors(group, result.errors)
      quoteStore.applySnapshotFallback(engineStore.market, config.snapshotKeys)
      quoteStore.persistCache()

      failures[group] = result.quotes.length ? 0 : failures[group] + 1
      return result
    }

    inFlight[group] = execute()
      .catch((error) => {
        failures[group] += 1
        quoteStore.applySnapshotFallback(engineStore.market, config.snapshotKeys)
        quoteStore.setProviderErrors(group, {
          scheduler: error instanceof Error ? error.message : 'Display quote yenilemesi başarısız.',
        })
        return null
      })
      .finally(() => {
        inFlight[group] = null
        schedule(group)
      })

    return inFlight[group]
  }

  function start() {
    if (active) return
    active = true
    for (const group of groups) void runGroup(group)
  }

  async function stop({ persist = true } = {}) {
    active = false
    for (const group of groups) clearTimer(group)
    if (persist) quoteStore.persistCache(true)
  }

  async function setActive(isActive) {
    if (isActive) {
      start()
      return
    }
    await stop()
  }

  async function refreshNow() {
    return Promise.allSettled(groups.map((group) => runGroup(group, { force: true })))
  }

  const scheduler = { start, stop, setActive, refreshNow }
  activeScheduler = scheduler
  return scheduler
}

export async function refreshDisplayQuotesNow() {
  if (!activeScheduler) return []
  return activeScheduler.refreshNow()
}
