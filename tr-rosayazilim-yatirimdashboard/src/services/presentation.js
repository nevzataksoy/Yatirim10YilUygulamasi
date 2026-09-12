export const TRANSACTION_TYPE_LABELS = {
  OPENING: 'Başlangıç',
  BUY: 'Alım',
  CONVERSION: 'Dönüşüm',
  SELL: 'Satış',
  EXIT: 'Çıkış',
  CASH_IN: 'Sermaye Girişi',
  CASH_OUT: 'Sermaye Çıkışı',
}

export const TRANSACTION_TYPE_TONES = {
  OPENING: 'neutral',
  BUY: 'primary',
  CONVERSION: 'info',
  SELL: 'warning',
  EXIT: 'negative',
  CASH_IN: 'positive',
  CASH_OUT: 'negative',
}

export const STATUS_LABELS = {
  OK: 'Sağlıklı',
  WAIT: 'Bekle',
  NO_ACTION_DATA: 'Veri Yetersiz',
  NOT_READY: 'Hazır Değil',
  READY: 'Hazır',
  DEGRADED: 'Kısıtlı',
  ERROR: 'Hata',
  FAILED: 'Başarısız',
  PASS: 'Başarılı',
  LIMITED: 'Sınırlı',
  SHADOW: 'Gölge',
}

export const STATUS_TONES = {
  OK: 'positive',
  PASS: 'positive',
  READY: 'positive',
  WAIT: 'info',
  SHADOW: 'info',
  NO_ACTION_DATA: 'warning',
  NOT_READY: 'warning',
  DEGRADED: 'warning',
  LIMITED: 'warning',
  ERROR: 'negative',
  FAILED: 'negative',
}

export const REGIME_LABELS = {
  RISK_ON_TREND: 'Risk Açık / Trend',
  RISK_OFF_TREND: 'Risk Kapalı / Trend',
  RANGE: 'Yatay Piyasa',
  TRANSITION: 'Geçiş',
  UNKNOWN: 'Bilinmiyor',
}

export const COMPONENT_LABELS = {
  ENGINE: 'Yatırım Motoru',
  CRYPTO: 'Kripto Verileri',
  CRYPTO_HISTORY: 'Kripto Geçmişi',
  FX: 'Döviz Kuru',
  MACRO: 'Makro Veriler',
  DERIVATIVES: 'Türev Verileri',
  URA: 'URA Verileri',
  SEC_EVENTS: 'SEC Olayları',
  MODEL_VALIDATION: 'Model Doğrulama',
}

export const VALIDATION_TYPE_LABELS = {
  SHADOW_READINESS: 'Gölge Hazırlık',
  HISTORICAL_CORE_REPLAY: 'Tarihsel Çekirdek Tekrarı',
  PIT_CORE_REPLAY: 'Noktasal Zaman Tekrarı',
  WALK_FORWARD: 'İleri Yürüyen Doğrulama',
}

export const SYSTEM_LABELS = {
  ALL: 'Tümü',
  'ETH/BTC': 'ETH/BTC',
  'URA/USD': 'URA/USD',
}

export const THRESHOLD_LABELS = {
  MIN_DATA_QUALITY: 'Minimum Veri Kalitesi',
  MIN_EDGE: 'Minimum Avantaj',
  MIN_CONFIDENCE: 'Minimum Güven',
  STRONG_EDGE: 'Güçlü Avantaj',
  STRONG_CONFIDENCE: 'Güçlü Güven',
}

export const METRIC_LABELS = {
  EDGE: 'Avantaj',
  CONFIDENCE: 'Güven',
  QUALITY: 'Veri Kalitesi',
}

export function labelFor(code, map, fallback = null) {
  if (!code) return fallback || '—'
  return map[code] || fallback || code
}

export function transactionTypeLabel(code) {
  return labelFor(code, TRANSACTION_TYPE_LABELS)
}

export function transactionTypeTone(code) {
  return TRANSACTION_TYPE_TONES[code] || 'neutral'
}

export function transactionAmountClass(code) {
  return `amount-${transactionTypeTone(code)}`
}

export function statusLabel(code) {
  return labelFor(code, STATUS_LABELS)
}

export function statusTone(code) {
  return STATUS_TONES[code] || 'neutral'
}

export function regimeLabel(code) {
  return labelFor(code, REGIME_LABELS)
}

export function componentLabel(code) {
  return labelFor(code, COMPONENT_LABELS)
}

export function validationTypeLabel(code) {
  return labelFor(code, VALIDATION_TYPE_LABELS)
}

export function systemLabel(code) {
  return labelFor(code, SYSTEM_LABELS)
}
