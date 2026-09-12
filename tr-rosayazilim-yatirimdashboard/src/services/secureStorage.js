import SecureLSModule from 'secure-ls'

const DEFAULT_SECRET = 'rosa-InvYat10yLS-v1'
const SecureLS = SecureLSModule?.default ?? SecureLSModule
const ENCRYPTION_SECRET = import.meta.env?.QCLI_SECURE_STORAGE_SECRET?.trim() || DEFAULT_SECRET

let secureStorage = null

function storageAvailable() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

function getStorage() {
  if (!storageAvailable()) return null
  if (!secureStorage) {
    secureStorage = new SecureLS({
      encodingType: 'aes',
      isCompression: true,
      encryptionSecret: ENCRYPTION_SECRET,
    })
  }
  return secureStorage
}

export function getSecureValue(key, fallback = null) {
  const storage = getStorage()
  if (!storage) return fallback
  try {
    const value = storage.get(key)
    return value === '' || value === null || value === undefined ? fallback : value
  } catch {
    removeSecureValue(key)
    return fallback
  }
}

export function setSecureValue(key, value) {
  try {
    getStorage()?.set(key, value)
    return true
  } catch {
    return false
  }
}

export function removeSecureValue(key) {
  try {
    getStorage()?.remove(key)
  } catch {
    // Storage failure must not break the in-memory app flow.
  }
}

export const supabaseSecureStorage = {
  getItem(key) {
    return getSecureValue(`supabase:${key}`, null)
  },
  setItem(key, value) {
    setSecureValue(`supabase:${key}`, value)
  },
  removeItem(key) {
    removeSecureValue(`supabase:${key}`)
  },
}
