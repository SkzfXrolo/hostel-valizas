const KEY = 'valizas-theme'

export function getTheme() {
  return localStorage.getItem(KEY) === 'night' ? 'night' : 'day'
}

export function applyTheme() {
  const theme = getTheme()
  document.documentElement.dataset.theme = theme
  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(theme === 'night'))
    btn.title = theme === 'night' ? 'Modo día' : 'Modo noche'
  })
}

export function toggleTheme() {
  const next = getTheme() === 'night' ? 'day' : 'night'
  localStorage.setItem(KEY, next)
  applyTheme()
}

export function setupTheme() {
  applyTheme()
  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    btn.addEventListener('click', toggleTheme)
  })
}
