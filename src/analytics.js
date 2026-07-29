/**
 * Lightweight analytics stub — replace PLAUSIBLE_DOMAIN to enable Plausible.
 * Tracks WhatsApp clicks as custom events when available.
 */
const PLAUSIBLE_DOMAIN = 'hostel-valizas.vercel.app'

export function setupAnalytics() {
  if (PLAUSIBLE_DOMAIN && !window.plausible) {
    const s = document.createElement('script')
    s.defer = true
    s.dataset.domain = PLAUSIBLE_DOMAIN
    s.src = 'https://plausible.io/js/script.js'
    document.head.appendChild(s)
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-wa], .fab-whatsapp, a[href*="wa.me"]')
    if (!a) return
    const context = a.getAttribute('data-wa-context') || document.body.dataset.page || 'unknown'
    track('WhatsApp Click', { context })
  })
}

export function track(name, props = {}) {
  try {
    if (typeof window.plausible === 'function') {
      window.plausible(name, { props })
    } else if (import.meta.env.DEV) {
      console.debug('[analytics]', name, props)
    }
  } catch {
    /* noop */
  }
}
