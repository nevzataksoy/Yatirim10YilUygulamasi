import { createClient } from '@supabase/supabase-js'
import {
  normalizeSupabaseConnection,
  testAuthenticatedSupabaseAccess,
  testSupabaseConnection,
} from '../src/services/supabase.js'

const requiredVariables = [
  'QCLI_SUPABASE_URL',
  'QCLI_SUPABASE_PUBLISHABLE_KEY',
  'QCLI_ACCEPTANCE_EMAIL',
  'QCLI_ACCEPTANCE_PASSWORD',
]

function fail(message) {
  throw new Error(message)
}

function requireEnvironment() {
  const missing = requiredVariables.filter((name) => !process.env[name]?.trim())
  if (missing.length) {
    fail(`Gerçek Supabase kabul testi için eksik ortam değişkenleri: ${missing.join(', ')}`)
  }

  return {
    connection: normalizeSupabaseConnection({
      url: process.env.QCLI_SUPABASE_URL,
      publishableKey: process.env.QCLI_SUPABASE_PUBLISHABLE_KEY,
    }),
    email: process.env.QCLI_ACCEPTANCE_EMAIL.trim(),
    password: process.env.QCLI_ACCEPTANCE_PASSWORD,
  }
}

async function verifyBootstrapRows(client, userId) {
  const [profile, accounts, settings, positions] = await Promise.all([
    client.from('profiles').select('user_id').eq('user_id', userId).maybeSingle(),
    client.from('investment_accounts').select('id,user_id,is_active').eq('user_id', userId),
    client.from('user_investment_settings').select('user_id').eq('user_id', userId).maybeSingle(),
    client.from('portfolio_positions').select('user_id,account_id,asset,quantity'),
  ])

  for (const result of [profile, accounts, settings, positions]) {
    if (result.error) throw result.error
  }
  if (profile.data?.user_id !== userId) fail('Auth trigger profile satırı bulunamadı.')
  if (!accounts.data?.length) fail('Auth kullanıcısı için yatırım hesabı bulunamadı.')
  if (accounts.data.some((row) => row.user_id !== userId)) {
    fail('RLS testi başka kullanıcıya ait yatırım hesabı döndürdü.')
  }
  if (settings.data?.user_id !== userId) fail('Kullanıcı yatırım ayarları satırı bulunamadı.')
  if (positions.data?.some((row) => row.user_id !== userId)) {
    fail('RLS testi başka kullanıcıya ait portföy pozisyonu döndürdü.')
  }

  return {
    accountCount: accounts.data.length,
    positionCount: positions.data?.length || 0,
  }
}

async function run() {
  const { connection, email, password } = requireEnvironment()
  const health = await testSupabaseConnection(connection)
  const client = createClient(connection.url, connection.publishableKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
      flowType: 'pkce',
    },
  })

  let signedIn = false
  try {
    const { data: signInData, error: signInError } = await client.auth.signInWithPassword({
      email,
      password,
    })
    if (signInError) throw signInError
    const userId = signInData.user?.id
    if (!userId || !signInData.session) fail('Supabase giriş yanıtı aktif oturum içermiyor.')
    signedIn = true

    const rls = await testAuthenticatedSupabaseAccess(client, userId)
    const bootstrap = await verifyBootstrapRows(client, userId)

    const { data: refreshData, error: refreshError } = await client.auth.refreshSession()
    if (refreshError) throw refreshError
    if (refreshData.user?.id !== userId || !refreshData.session?.access_token) {
      fail('Token refresh sonrasında kullanıcı oturumu korunmadı.')
    }

    await client.auth.signOut({ scope: 'local' })
    signedIn = false
    const { data: afterSignOut, error: sessionError } = await client.auth.getSession()
    if (sessionError) throw sessionError
    if (afterSignOut.session) fail('Yerel sign-out sonrasında oturum temizlenmedi.')

    console.log(
      JSON.stringify(
        {
          status: 'PASS',
          authHealth: health.authApi,
          authenticatedRls: rls.authenticatedRls,
          accountCount: bootstrap.accountCount,
          positionCount: bootstrap.positionCount,
          tokenRefresh: 'PASS',
          localSignOut: 'PASS',
          checkedAt: new Date().toISOString(),
        },
        null,
        2,
      ),
    )
  } finally {
    if (signedIn) await client.auth.signOut({ scope: 'local' }).catch(() => undefined)
  }
}

run().catch((error) => {
  console.error(`ACCEPTANCE FAIL: ${error instanceof Error ? error.message : String(error)}`)
  process.exitCode = 1
})
