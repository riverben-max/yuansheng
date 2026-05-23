export function splitHighlightText(text, keyword) {
  const source = String(text || '')
  const query = String(keyword || '')
  if (!source || !query) {
    return [{ text: source, highlighted: false }]
  }

  const lowerSource = source.toLowerCase()
  const lowerQuery = query.toLowerCase()
  const parts = []
  let start = 0
  let index = lowerSource.indexOf(lowerQuery)

  while (index !== -1) {
    if (index > start) {
      parts.push({ text: source.slice(start, index), highlighted: false })
    }
    parts.push({ text: source.slice(index, index + query.length), highlighted: true })
    start = index + query.length
    index = lowerSource.indexOf(lowerQuery, start)
  }

  if (start < source.length) {
    parts.push({ text: source.slice(start), highlighted: false })
  }
  return parts.length ? parts : [{ text: source, highlighted: false }]
}
