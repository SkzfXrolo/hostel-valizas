/**
 * Privacy-friendly analytics (Plausible).
 * Tracks pageviews + WhatsApp clicks as custom events.
 */

const PLAUSIBLE_SCRIPT = 'https://plausible.io/js/pa-m0mBsC9BZK-2hOMozWWdu.js'

export function setupAnalytics() {
  if (window.plausible?.init || document.querySelector(`script[src="${PLAUSIBLE_SCRIPT}"]`)) {
    return
  }

  window.plausible =
    window.plausible ||
    function () {
      ;(window.plausible.q = window.plausible.q || []).push(arguments)
    }
  window.plausible.init = window.plausible.init || function (i) {
    window.plausible.o = i || {}
  }
  window.plausible.init()

  const s = document.createElement('script')
  s.async = true
  s.src = PLAUSIBLE_SCRIPT
  document.head.appendChild(s)

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
