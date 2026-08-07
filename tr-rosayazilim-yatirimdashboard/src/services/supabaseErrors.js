const NETWORK_PATTERNS = [
  'failed to fetch',
  'fetch failed',
  'networkerror',
  'network request failed',
  'load failed',
]

function includesAny(value, patterns) {
  return patterns.some((pattern) => value.includes(pattern))
}

export function classifySupabaseError(error, fallback = 'Supabase işlemi başarısız.') {
  if (error?.kind && error?.message) {
    return {
      kind: error.kind,
      message: error.message,
      retryable: Boolean(error.retryable),
    }
  }

  const message = String(error?.message || fallback)
  const normalized = message.toLocaleLowerCase('tr-TR')
  const code = String(error?.code || '')
  const status = Number(error?.status || error?.statusCode || 0)
  const name = String(error?.name || '')

  if (
    name === 'AbortError' ||
    normalized.includes('zaman aşımı') ||
    normalized.includes('timeout')
  ) {
    return {
      kind: 'TIMEOUT',
      message:
        'Supabase bağlantısı zaman aşımına uğradı. Ağ bağlantısını kontrol edip tekrar dene.',
      retryable: true,
    }
  }

  if (includesAny(normalized, NETWORK_PATTERNS)) {
    return {
      kind: 'NETWORK',
      message:
        'Supabase sunucusuna ulaşılamadı. İnternet bağlantısını ve Project URL bilgisini kontrol et.',
      retryable: true,
    }
  }

  if (
    code === 'invalid_api_key' ||
    normalized.includes('invalid api key') ||
    normalized.includes('no api key found')
  ) {
    return {
      kind: 'INVALID_KEY',
      message: 'Publishable/anon key geçersiz veya bu Supabase projesine ait değil.',
      retryable: false,
    }
  }

  if (code === '42501' || status === 403 || normalized.includes('row-level security')) {
    return {
      kind: 'RLS_DENIED',
      message: 'Oturum açıldı ancak Supabase RLS politikası uygulama verilerine erişimi reddetti.',
      retryable: false,
    }
  }

  if (
    code === 'refresh_token_not_found' ||
    code === 'refresh_token_already_used' ||
    normalized.includes('jwt expired') ||
    normalized.includes('invalid jwt') ||
    normalized.includes('session from session_id claim in jwt does not exist')
  ) {
    return {
      kind: 'SESSION_EXPIRED',
      message: 'Oturumun süresi doldu veya yenileme anahtarı geçersiz. Lütfen yeniden giriş yap.',
      retryable: false,
    }
  }

  if (code === 'session_not_found' || normalized.includes('auth session missing')) {
    return {
      kind: 'SESSION_MISSING',
      message: 'Aktif Supabase oturumu bulunamadı. Lütfen yeniden giriş yap.',
      retryable: false,
    }
  }

  if (code === 'email_not_confirmed' || normalized.includes('email not confirmed')) {
    return {
      kind: 'EMAIL_NOT_CONFIRMED',
      message: 'E-posta adresi henüz doğrulanmamış. Gelen kutundaki doğrulama bağlantısını aç.',
      retryable: false,
    }
  }

  if (code === 'invalid_credentials' || normalized.includes('invalid login credentials')) {
    return {
      kind: 'INVALID_CREDENTIALS',
      message: 'E-posta veya şifre hatalı.',
      retryable: false,
    }
  }

  if (status === 401) {
    return {
      kind: 'UNAUTHORIZED',
      message:
        'Supabase isteği yetkilendirilemedi. Oturumu ve publishable key bilgisini kontrol et.',
      retryable: false,
    }
  }

  return { kind: 'UNKNOWN', message, retryable: false }
}

export function asSupabaseAppError(error, fallback) {
  const classified = classifySupabaseError(error, fallback)
  const wrapped = new Error(classified.message, { cause: error })
  wrapped.kind = classified.kind
  wrapped.retryable = classified.retryable
  wrapped.originalCode = error?.code || null
  wrapped.status = error?.status || error?.statusCode || null
  return wrapped
}
