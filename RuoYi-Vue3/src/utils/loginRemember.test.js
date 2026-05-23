import test from 'node:test'
import assert from 'node:assert/strict'

import { persistRememberedLoginForm, restoreRememberedLoginForm } from './loginRemember.js'

function fakeCookies(initial = {}) {
  const values = { ...initial }
  const calls = []
  return {
    calls,
    get(key) {
      return values[key]
    },
    set(key, value, options) {
      calls.push(['set', key, value, options])
      values[key] = value
    },
    remove(key) {
      calls.push(['remove', key])
      delete values[key]
    }
  }
}

test('restoreRememberedLoginForm never restores password from cookie', () => {
  const cookies = fakeCookies({
    username: 'manager',
    password: 'encrypted-password',
    rememberMe: 'true'
  })

  const form = restoreRememberedLoginForm(
    { username: '', password: 'typed-password', rememberMe: false, code: '1234', uuid: 'u1' },
    cookies
  )

  assert.equal(form.username, 'manager')
  assert.equal(form.password, '')
  assert.equal(form.rememberMe, true)
  assert.equal(form.code, '1234')
  assert.equal(form.uuid, 'u1')
})

test('persistRememberedLoginForm saves username only and removes legacy password cookie', () => {
  const cookies = fakeCookies()

  persistRememberedLoginForm({ username: 'manager', password: 'secret', rememberMe: true }, cookies)

  assert.deepEqual(cookies.calls, [
    ['set', 'username', 'manager', { expires: 30 }],
    ['set', 'rememberMe', 'true', { expires: 30 }],
    ['remove', 'password']
  ])
})
