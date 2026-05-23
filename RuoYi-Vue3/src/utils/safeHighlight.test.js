import test from 'node:test'
import assert from 'node:assert/strict'

import { splitHighlightText } from './safeHighlight.js'

test('splitHighlightText returns text parts instead of HTML strings', () => {
  const parts = splitHighlightText('<img src=x onerror=alert(1)>系统', '系统')

  assert.deepEqual(parts, [
    { text: '<img src=x onerror=alert(1)>', highlighted: false },
    { text: '系统', highlighted: true }
  ])
})

test('splitHighlightText highlights repeated case-insensitive matches', () => {
  const parts = splitHighlightText('User user USER', 'user')

  assert.deepEqual(parts, [
    { text: 'User', highlighted: true },
    { text: ' ', highlighted: false },
    { text: 'user', highlighted: true },
    { text: ' ', highlighted: false },
    { text: 'USER', highlighted: true }
  ])
})
