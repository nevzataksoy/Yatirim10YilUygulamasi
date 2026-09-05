import assert from 'node:assert/strict'
import test from 'node:test'
import { buildAuthCallbackUrl, normalizeSupabaseConnection } from '../src/services/supabase.js'
import { classifySupabaseError } from '../src/services/supabaseErrors.js'

test('Supabase connection values are normalized', () => {
  assert.deepEqual(
    normalizeSupabaseConnection({
      url: ' https://example.supabase.co/// ',
      publishableKey: ' publishable-key ',
    }),
    {
      url: 'https://example.supabase.co',
      publishableKey: 'publishable-key',
    },
  )
})

test('service role keys are rejected before client creation', () => {
  assert.throws(
    () =>
      normalizeSupabaseConnection({
        url: 'https://example.supabase.co',
        publishableKey: 'sb_secret_do-not-store-this',
      }),
    /service_role veya secret key/,
  )
})

test('SPA and native callback URLs keep their requested flow', () => {
  assert.equal(
    buildAuthCallbackUrl('https://app.example.com/#/auth/callback', 'recovery'),
    'https://app.example.com/#/auth/callback?flow=recovery',
  )
  assert.equal(
    buildAuthCallbackUrl('tr.rosayazilim.yatirimdashboard://auth/callback', 'confirmation'),
    'tr.rosayazilim.yatirimdashboard://auth/callback?flow=confirmation',
  )
})

test('Supabase failures are mapped to actionable error classes', () => {
  assert.equal(classifySupabaseError({ name: 'AbortError' }).kind, 'TIMEOUT')
  assert.equal(classifySupabaseError({ message: 'Failed to fetch' }).kind, 'NETWORK')
  assert.equal(classifySupabaseError({ code: '42501' }).kind, 'RLS_DENIED')
  assert.equal(classifySupabaseError({ code: 'invalid_credentials' }).kind, 'INVALID_CREDENTIALS')
})
