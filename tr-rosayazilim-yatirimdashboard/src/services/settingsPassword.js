import { getSecureValue, setSecureValue } from './secureStorage'

const SETTINGS_PASSWORD_KEY = 'app:settings-password-verifier'
const VERIFIER_VERSION = 1
const PBKDF2_ITERATIONS = 210_000
const SALT_BYTES = 16
const HASH_BITS = 256

export const MIN_SETTINGS_PASSWORD_LENGTH = 6

function getWebCrypto() {
  const webCrypto = globalThis.crypto
  if (!webCrypto?.subtle || typeof webCrypto.getRandomValues !== 'function') {
    throw new Error('Bu cihaz güvenli ayar şifresi doğrulamasını desteklemiyor.')
  }
  return webCrypto
}

function bytesToBase64(bytes) {
  return globalThis.btoa(String.fromCharCode(...bytes))
}

function base64ToBytes(value) {
  return Uint8Array.from(globalThis.atob(value), (character) => character.charCodeAt(0))
}

async function deriveVerifier(password, salt, iterations) {
  const webCrypto = getWebCrypto()
  const passwordKey = await webCrypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(password),
    'PBKDF2',
    false,
    ['deriveBits'],
  )
  const bits = await webCrypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      hash: 'SHA-256',
      salt,
      iterations,
    },
    passwordKey,
    HASH_BITS,
  )
  return new Uint8Array(bits)
}

function isVerifierRecord(value) {
  return Boolean(
    value &&
    value.version === VERIFIER_VERSION &&
    Number.isInteger(value.iterations) &&
    value.iterations > 0 &&
    typeof value.salt === 'string' &&
    value.salt &&
    typeof value.verifier === 'string' &&
    value.verifier,
  )
}

function equalBytes(left, right) {
  if (left.length !== right.length) return false
  let difference = 0
  for (let index = 0; index < left.length; index += 1) {
    difference |= left[index] ^ right[index]
  }
  return difference === 0
}

export function hasSettingsPassword() {
  return isVerifierRecord(getSecureValue(SETTINGS_PASSWORD_KEY, null))
}

export async function setSettingsPassword(password) {
  const normalizedPassword = String(password ?? '')
  if (normalizedPassword.length < MIN_SETTINGS_PASSWORD_LENGTH) {
    throw new Error(`Ayar şifresi en az ${MIN_SETTINGS_PASSWORD_LENGTH} karakter olmalı.`)
  }

  const webCrypto = getWebCrypto()
  const salt = webCrypto.getRandomValues(new Uint8Array(SALT_BYTES))
  const verifier = await deriveVerifier(normalizedPassword, salt, PBKDF2_ITERATIONS)
  const stored = setSecureValue(SETTINGS_PASSWORD_KEY, {
    version: VERIFIER_VERSION,
    algorithm: 'PBKDF2-SHA256',
    iterations: PBKDF2_ITERATIONS,
    salt: bytesToBase64(salt),
    verifier: bytesToBase64(verifier),
  })

  if (!stored) throw new Error('Ayar şifresi bu cihazda saklanamadı.')
}

export async function verifySettingsPassword(password) {
  const record = getSecureValue(SETTINGS_PASSWORD_KEY, null)
  if (!isVerifierRecord(record)) return false

  try {
    const actual = await deriveVerifier(
      String(password ?? ''),
      base64ToBytes(record.salt),
      record.iterations,
    )
    return equalBytes(actual, base64ToBytes(record.verifier))
  } catch {
    return false
  }
}
