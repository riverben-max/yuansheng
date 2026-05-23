import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const currentDir = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(currentDir, '..', '..', '..')

function readRepoFile(relativePath) {
  return readFileSync(resolve(repoRoot, relativePath), 'utf8')
}

test('cloud doc controller sanitizes rich text before returning it to v-html preview', () => {
  const source = readRepoFile('RuoYi-Vue/ruoyi-admin/src/main/java/com/ruoyi/qingbird/controller/BizCloudDocController.java')

  assert.equal(source.includes('EscapeUtil.clean'), true)
  assert.equal(source.includes('sanitizeDoc'), true)
})

test('branch manager creation no longer defaults to weak 123456 password', () => {
  const frontend = readRepoFile('RuoYi-Vue3/src/views/qingbird/branch/index.vue')
  const backend = readRepoFile('RuoYi-Vue/ruoyi-admin/src/main/java/com/ruoyi/qingbird/service/impl/BizBranchInfoServiceImpl.java')

  assert.equal(frontend.includes("managerPassword: '123456'"), false)
  assert.equal(frontend.includes("form.value.managerPassword = '123456'"), false)
  assert.equal(frontend.includes('默认建议：123456'), false)
  assert.equal(backend.includes('InitialPasswordPolicy.isWeak'), true)
})

test('seat account creation requires explicit non-default initial password', () => {
  const frontend = readRepoFile('RuoYi-Vue3/src/views/qingbird/seat/index.vue')
  const backend = readRepoFile('RuoYi-Vue/ruoyi-admin/src/main/java/com/ruoyi/qingbird/service/impl/BizEmployeeServiceImpl.java')

  assert.equal(frontend.includes('初始密码为：<strong>123456</strong>'), false)
  assert.equal(backend.includes('getInitialPassword'), true)
  assert.equal(backend.includes('encryptPassword("123456")'), false)
})
