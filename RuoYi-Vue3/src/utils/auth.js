import Cookies from 'js-cookie'

const TokenKey = 'Admin-Token'

export function getToken() {
  return Cookies.get(TokenKey)
}

export function buildTokenCookieOptions(protocol = globalThis.location?.protocol) {
  return {
    path: '/',
    sameSite: 'Lax',
    secure: protocol === 'https:'
  }
}

export function setToken(token) {
  return Cookies.set(TokenKey, token, buildTokenCookieOptions())
}

export function removeToken() {
  return Cookies.remove(TokenKey, buildTokenCookieOptions())
}
