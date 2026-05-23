export function restoreRememberedLoginForm(currentForm, cookies) {
  const username = cookies.get('username')
  const rememberMe = cookies.get('rememberMe')
  return {
    ...currentForm,
    username: username === undefined ? currentForm.username : username,
    password: '',
    rememberMe: rememberMe === 'true'
  }
}

export function persistRememberedLoginForm(form, cookies) {
  if (form.rememberMe) {
    cookies.set('username', form.username, { expires: 30 })
    cookies.set('rememberMe', 'true', { expires: 30 })
  } else {
    cookies.remove('username')
    cookies.remove('rememberMe')
  }
  cookies.remove('password')
}
