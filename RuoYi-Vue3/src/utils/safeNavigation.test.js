import test from 'node:test'
import assert from 'node:assert/strict'

import { parseRouteQuery, externalWindowFeatures } from './safeNavigation.js'

test('parseRouteQuery returns parsed object for valid route query json', () => {
  assert.deepEqual(parseRouteQuery('{"tab":"profile","page":2}'), { tab: 'profile', page: 2 })
})

test('parseRouteQuery returns empty object for malformed or non-object json', () => {
  assert.deepEqual(parseRouteQuery('{bad json'), {})
  assert.deepEqual(parseRouteQuery('[1,2]'), {})
  assert.deepEqual(parseRouteQuery(''), {})
})

test('externalWindowFeatures protects opened links', () => {
  assert.equal(externalWindowFeatures, 'noopener,noreferrer')
})
