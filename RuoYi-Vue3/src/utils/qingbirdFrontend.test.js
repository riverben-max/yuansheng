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

test('seat page has no hard-coded branch fallback and gates non-admin business calls on my branch info', () => {
  const source = readSource('views/qingbird/seat/index.vue')

  assert.equal(source.includes('DEFAULT_BRANCH_CODE'), false)
  assert.equal(source.includes('B-1773208272961'), false)
  assert.equal(source.includes('branchScopeReady'), true)
  assert.equal(source.includes('ensureBranchScope'), true)
})

test('seat operation buttons use permission directives instead of role checks', () => {
  const source = readSource('views/qingbird/seat/index.vue')

  for (const perm of [
    'qingbird:employee:add',
    'qingbird:employee:edit',
    'qingbird:employee:remove',
    'qingbird:employee:export'
  ]) {
    assert.equal(source.includes(perm), true)
  }
})

test('qc detail uses single-day recordDate filter because backend has no range parameters', () => {
  const source = readSource('views/qingbird/qcDetail/index.vue')

  assert.equal(source.includes('type="daterange"'), false)
  assert.equal(source.includes('dateRange'), false)
  assert.equal(source.includes('params.recordDate = queryForm.value.recordDate'), true)
})

test('qc detail only degrades explicit endpoint-not-ready errors', () => {
  const source = readSource('views/qingbird/qcDetail/index.vue')

  assert.equal(source.includes('isEndpointNotReadyError'), true)
  assert.equal(source.includes('接口未就绪时显示空表格'), false)
})

test('qingbird branch info api only hides explicit not-found endpoint errors', () => {
  const source = readSource('api/qingbird/branchInfo.js')

  assert.equal(source.includes('hideErrorMsg: true'), false)
  assert.equal(source.includes('hideErrorCodes: [404]'), true)
})

test('qc detail request only suppresses explicit not-found endpoint errors', () => {
  const source = readSource('views/qingbird/qcDetail/index.vue')

  assert.equal(source.includes("url: '/qingbird/spider-data/list'"), true)
  assert.equal(source.includes('hideErrorMsg: true'), false)
  assert.equal(source.includes('hideErrorCodes: [404]'), true)
})
