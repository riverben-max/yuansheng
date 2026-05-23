import DOMPurify from 'dompurify'

const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'span', 'div', 'blockquote',
  'pre', 'code', 'ul', 'ol', 'li', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5',
  'h6', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
]

const ALLOWED_TAG_NAMES = new Set(ALLOWED_TAGS)
const ALLOWED_ATTR = ['href', 'src', 'title', 'alt', 'width', 'height']
const DANGEROUS_CONTENT_TAGS = /<(script|style)\b[\s\S]*?<\/\1>/gi
const HTML_TAG = /<\/?\s*([A-Za-z][\w:-]*)(?:\s[^>]*)?>/g

let linkHookInstalled = false

function ensureLinkHook() {
  if (linkHookInstalled) return
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node?.tagName === 'A' && node.getAttribute('href')) {
      node.setAttribute('target', '_blank')
      node.setAttribute('rel', 'noopener noreferrer')
    }
  })
  linkHookInstalled = true
}

function unwrapUnsupportedTags(html) {
  return String(html || '')
    .replace(DANGEROUS_CONTENT_TAGS, '')
    .replace(HTML_TAG, (token, tagName) => (ALLOWED_TAG_NAMES.has(String(tagName).toLowerCase()) ? token : ''))
}

export function sanitizeRichText(html) {
  if (!html) return ''
  ensureLinkHook()
  return DOMPurify.sanitize(unwrapUnsupportedTags(html), {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false
  })
}
