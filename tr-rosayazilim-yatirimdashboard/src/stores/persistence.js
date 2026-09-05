import { getSecureValue, setSecureValue } from '@/services/secureStorage'

const persistedStores = {
  auth: ['cachedUser', 'demoSession'],
  portfolio: [
    'selectedAccountId',
    'accounts',
    'transactions',
    'settings',
    'demoDataRevision',
    'lastSyncAt',
  ],
  engine: ['market', 'decisions', 'health', 'validation', 'lastSyncAt'],
  ui: ['displayAsset'],
}

function selectState(state, keys) {
  return Object.fromEntries(keys.map((key) => [key, state[key]]))
}

export function securePiniaPersistence({ store }) {
  const keys = persistedStores[store.$id]
  if (!keys) return

  const storageKey = `pinia:${store.$id}`
  const cached = getSecureValue(storageKey, null)
  if (cached && typeof cached === 'object') store.$patch(cached)

  store.$subscribe((_mutation, state) => setSecureValue(storageKey, selectState(state, keys)), {
    detached: true,
  })
}
