/** Canonical site origin. Set VITE_SITE_URL when the final domain is ready. */
const FALLBACK = 'https://hostel-valizas.vercel.app'

function normalizeSiteUrl(value) {
  let url = String(value || '').trim()
  url = url.replace(/^VITE_SITE_URL\s*=\s*/i, '').trim()
  return url.replace(/\/$/, '')
}

export function getSiteUrl() {
  const preferred = import.meta.env.VITE_SITE_URL
  if (preferred) {
    const url = normalizeSiteUrl(preferred)
    if (url) return url
  }
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin
  }
  return FALLBACK
}
