export const externalWindowFeatures = 'noopener,noreferrer'

export function parseRouteQuery(query) {
  if (!query) return {}
  try {
    const parsed = JSON.parse(query)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {}
    }
    return parsed
  } catch (error) {
    return {}
  }
}
