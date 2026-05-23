import test from 'node:test'
import assert from 'node:assert/strict'

import { buildTokenCookieOptions } from './auth.js'

test('buildTokenCookieOptions sets path, sameSite and secure on https', () => {
  assert.deepEqual(buildTokenCookieOptions('https:'), { path: '/', sameSite: 'Lax', secure: true })
})

test('buildTokenCookieOptions keeps local http usable without secure flag', () => {
  assert.deepEqual(buildTokenCookieOptions('http:'), { path: '/', sameSite: 'Lax', secure: false })
})
