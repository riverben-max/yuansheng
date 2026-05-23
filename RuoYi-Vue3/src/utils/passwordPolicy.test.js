import test from 'node:test'
import assert from 'node:assert/strict'

import { validateInitialPassword } from './passwordPolicy.js'

test('validateInitialPassword rejects missing or short passwords', () => {
  assert.equal(validateInitialPassword('').valid, false)
  assert.equal(validateInitialPassword('Ab1!').message, '初始密码长度至少 8 位')
})

test('validateInitialPassword rejects whitespace and common weak passwords', () => {
  assert.equal(validateInitialPassword('Abc 1234!').message, '初始密码不能包含空白字符')
  assert.equal(validateInitialPassword('Password123!').message, '不能使用常见弱密码')
})

test('validateInitialPassword requires mixed character classes', () => {
  assert.equal(validateInitialPassword('abcdefgh').message, '初始密码需包含大写字母、小写字母、数字、特殊字符中的至少 3 类')
  assert.equal(validateInitialPassword('Abcdefg1').valid, true)
})

test('validateInitialPassword rejects passwords containing account name', () => {
  assert.equal(validateInitialPassword('Alice_2026!', 'alice').message, '初始密码不能包含登录账号')
  assert.equal(validateInitialPassword('N9!xKp2z', 'alice').valid, true)
})
