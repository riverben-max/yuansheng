const COMMON_WEAK_PASSWORDS = new Set([
  '123456',
  '1234567',
  '12345678',
  '123456789',
  '111111',
  '000000',
  'password',
  'password1',
  'password123',
  'admin',
  'admin123',
  'qwerty',
  'qwerty123',
  'abc123',
  'abc123456',
  'iloveyou',
  'welcome',
  'letmein'
])

export function validateInitialPassword(value, account = '') {
  const password = String(value || '')
  const loginAccount = String(account || '').trim().toLowerCase()

  if (!password) {
    return { valid: false, message: '初始密码不能为空' }
  }
  if (password.length < 8) {
    return { valid: false, message: '初始密码长度至少 8 位' }
  }
  if (/\s/.test(password)) {
    return { valid: false, message: '初始密码不能包含空白字符' }
  }

  const normalized = password.toLowerCase()
  const compact = normalized.replace(/[^a-z0-9]/g, '')
  if (COMMON_WEAK_PASSWORDS.has(normalized) || COMMON_WEAK_PASSWORDS.has(compact)) {
    return { valid: false, message: '不能使用常见弱密码' }
  }
  if (loginAccount && loginAccount.length >= 3 && normalized.includes(loginAccount)) {
    return { valid: false, message: '初始密码不能包含登录账号' }
  }

  const classes = [/[a-z]/.test(password), /[A-Z]/.test(password), /\d/.test(password), /[^A-Za-z0-9]/.test(password)]
  if (classes.filter(Boolean).length < 3) {
    return { valid: false, message: '初始密码需包含大写字母、小写字母、数字、特殊字符中的至少 3 类' }
  }

  return { valid: true, message: '' }
}
