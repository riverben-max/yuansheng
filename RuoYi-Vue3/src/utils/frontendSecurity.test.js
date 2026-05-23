import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const currentDir = dirname(fileURLToPath(import.meta.url))
const srcDir = resolve(currentDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(srcDir, relativePath), 'utf8')
}

test('login page does not ship default credentials or persist password cookies', () => {
  const source = readSource('views/login.vue')

  assert.equal(source.includes('admin123'), false)
  assert.equal(source.includes('username: "admin"'), false)
  assert.equal(source.includes('Cookies.set("password"'), false)
  assert.equal(source.includes('decrypt(password)'), false)
})

test('header search renders highlighted text without v-html', () => {
  const source = readSource('components/HeaderSearch/index.vue')

  assert.equal(source.includes('v-html'), false)
  assert.equal(source.includes('splitHighlightText'), true)
})
