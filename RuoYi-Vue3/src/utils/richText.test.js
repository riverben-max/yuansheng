import test from 'node:test'
import assert from 'node:assert/strict'
import { JSDOM } from 'jsdom'

const dom = new JSDOM('<!doctype html><html><body></body></html>')
globalThis.window = dom.window
globalThis.document = dom.window.document
globalThis.Node = dom.window.Node

const { sanitizeRichText } = await import('./richText.js')

test('sanitizeRichText keeps basic rich text tags', () => {
  const html = '<p><strong>标题</strong><br><a href="https://example.com">链接</a></p><ul><li>项</li></ul>'

  assert.equal(sanitizeRichText(html), '<p><strong>标题</strong><br><a href="https://example.com" target="_blank" rel="noopener noreferrer">链接</a></p><ul><li>项</li></ul>')
})

test('sanitizeRichText removes scripts, event handlers and javascript urls', () => {
  const html = '<p onclick="alert(1)">正文<script>alert(1)</script><img src="x" onerror="alert(2)"><a href="javascript:alert(3)">bad</a></p>'

  assert.equal(sanitizeRichText(html), '<p>正文<img src="x"><a>bad</a></p>')
})

test('sanitizeRichText escapes unknown tags but keeps their text', () => {
  assert.equal(sanitizeRichText('<iframe src="x"><b>保留文字</b></iframe><span style="color:red">ok</span>'), '<b>保留文字</b><span>ok</span>')
})
