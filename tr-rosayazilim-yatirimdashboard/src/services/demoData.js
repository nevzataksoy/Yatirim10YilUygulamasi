const now = new Date().toISOString()
const accountId = 'demo-main-account'
const userId = 'demo-user'
const demoUsdTry = 47.4

export const DEMO_DATA_REVISION = '2026-07-31-empty-portfolio-100k-try-v1'

export const demoAccount = {
  id: accountId,
  user_id: userId,
  name: '10 Yıllık Yatırım Portföyü',
  base_currency: 'USD',
  is_active: true,
}

export const demoSettings = {
  monthly_budget_usd: 100000 / demoUsdTry,
  start_date: '2026-07-25',
  btc_target_pct: 37.5,
  eth_target_pct: 37.5,
  ura_target_pct: 25,
  btc_eth_conversion_pct: 50,
  ura_usd_conversion_pct: 50,
  dca_day: 25,
  telegram_notifications: true,
}

// Demo portföyü bilinçli olarak boş başlar. Kullanıcının test senaryosundaki
// tüm bakiye, maliyet, dönüşüm, satış ve sermaye hesapları gerçek girişlerden oluşur.
export const demoTransactions = []

// Portföy testlerinin güncel değer/P&L tarafını çalıştırabilmesi için piyasa snapshot'ı
// demo modunda tutulur. Bunlar gerçek zamanlı fiyat iddiası değil, sabit test değerleridir.
export const demoMarket = [
  ['BTC/USD', 64800, 'USD'],
  ['ETH/USD', 1920, 'USD'],
  ['ETH/BTC', 0.02963, 'RATIO'],
  ['URA/USD', 37.5, 'USD'],
  ['USD/TRY', demoUsdTry, 'TRY'],
].map(([symbol, value, unit]) => ({
  symbol,
  value,
  unit,
  provider: 'demo',
  data_date: '2026-07-31',
  generated_at: now,
}))

export const demoDecisions = [
  {
    system: 'ETH/BTC',
    as_of: '2026-07-30',
    direction: 'BTC→ETH',
    status: 'WAIT',
    regime_code: 'RISK_ON_TREND',
    edge_score: 35.64,
    confidence: 46.25,
    data_quality: 90.45,
    risk_score: 37.7,
    model_version: '1.2.0',
    generated_at: now,
  },
  {
    system: 'URA/USD',
    as_of: '2026-07-30',
    direction: 'URA→USD',
    status: 'NO_ACTION_DATA',
    regime_code: 'RISK_ON_TREND',
    edge_score: 33.99,
    confidence: 36.17,
    data_quality: 70.4,
    risk_score: 40.9,
    model_version: '1.2.0',
    generated_at: now,
  },
]

export const demoHealth = [
  ['ENGINE', 'OK', 'Gölge yatırım motoru aktif'],
  ['CRYPTO', 'OK', 'Kripto günlük veri ve karar döngüsü çalışıyor'],
  ['DERIVATIVES', 'OK', 'OKX yedek veri kaynağı aktif'],
  ['MACRO', 'OK', 'FRED serileri güncel'],
  ['SEC_EVENTS', 'DEGRADED', 'SEC olay kapsamı kısmi'],
].map(([component, status, message]) => ({ component, status, message, checked_at: now }))

export const demoValidation = [
  {
    validation_type: 'SHADOW_READINESS',
    system: 'ALL',
    model_version: '1.2.0',
    status: 'NOT_READY',
    generated_at: now,
    metrics: {
      stats: {
        calendar_days: 1,
        crypto_decision_days: 1,
        ura_decision_days: 1,
        ura_holdings_dates: 1,
        ura_breadth_dates: 1,
        crypto_median_quality: 90.45,
        ura_median_quality: 70.4,
      },
      waiting_reasons: ['Gölge gözlem süresi devam ediyor.'],
    },
  },
]
