export const ADMIN_CONTENT_KEY = 'valizas-admin-content'
export const ADMIN_SESSION_KEY = 'valizas-admin-session'
export const ADMIN_TOKEN_KEY = 'valizas-admin-token'
export const ADMIN_TOKEN_EXP_KEY = 'valizas-admin-token-exp'

/** Defaults shipped with the site — admin overrides via localStorage / content.json */
export const DEFAULTS = {
  version: 1,
  usdToUyu: 42,
  blockedDates: [
    '2026-01-01',
    '2026-01-02',
    '2026-01-03',
    '2026-02-14',
    '2026-02-15',
    '2026-07-18',
    '2026-07-19',
    '2026-12-24',
    '2026-12-25',
    '2026-12-31',
  ],
  rateMonths: {
    1: { season: 'alta', suite: [110, 130], doble: [90, 110], dorm: [30, 40] },
    2: { season: 'alta', suite: [105, 125], doble: [85, 105], dorm: [28, 38] },
    3: { season: 'media', suite: [80, 100], doble: [65, 85], dorm: [22, 30] },
    4: { season: 'media', suite: [75, 95], doble: [60, 80], dorm: [20, 28] },
    5: { season: 'baja', suite: [60, 80], doble: [48, 65], dorm: [16, 22] },
    6: { season: 'baja', suite: [58, 78], doble: [45, 62], dorm: [15, 21] },
    7: { season: 'media', suite: [78, 98], doble: [62, 82], dorm: [22, 30] },
    8: { season: 'baja', suite: [60, 80], doble: [48, 65], dorm: [16, 22] },
    9: { season: 'baja', suite: [62, 82], doble: [50, 68], dorm: [17, 23] },
    10: { season: 'baja', suite: [65, 85], doble: [52, 70], dorm: [18, 24] },
    11: { season: 'media', suite: [78, 98], doble: [62, 82], dorm: [22, 30] },
    12: { season: 'alta', suite: [100, 130], doble: [80, 110], dorm: [26, 40] },
  },
  googleRating: { score: 4.2, reviewCount: 180 },
  curatedReviews: [
    {
      id: 'c1',
      name: 'Camila R.',
      origin: 'AR',
      rating: 5,
      date: '2026-03-12',
      source: 'Google',
      text: {
        es: 'Ubicación impecable, a metros de la playa y del centro. El ambiente es re amigable y la pileta al final del día es un golazo. Volveríamos sin dudarlo.',
        en: 'Impeccable location, meters from the beach and the center. Friendly vibe and the pool at the end of the day is a win. We would come back anytime.',
        pt: 'Localização impecável, a metros da praia e do centro. Clima super amigável e a piscina no fim do dia é um gol. Voltaríamos sem dúvida.',
      },
    },
    {
      id: 'c2',
      name: 'Mateo S.',
      origin: 'UY',
      rating: 5,
      date: '2026-02-28',
      source: 'Google',
      text: {
        es: 'Atendido por los dueños, súper atentos con tips de dunas y Cabo Polonio. Ideal si venís a conocer gente y vivir Valizas de verdad.',
        en: 'Owner-run and super helpful with dune and Cabo Polonio tips. Ideal if you want to meet people and really live Valizas.',
        pt: 'Atendido pelos donos, super atentos com dicas de dunas e Cabo Polonio. Ideal para conhecer gente e viver Valizas de verdade.',
      },
    },
    {
      id: 'c3',
      name: 'Lucía F.',
      origin: 'UY',
      rating: 4,
      date: '2026-02-10',
      source: 'Google',
      text: {
        es: 'Hostel con mucha onda, LGBTQ+ friendly y pet friendly. Habitación privada cómoda y desayuno incluido. Buen punto de partida para las dunas.',
        en: 'Great vibe hostel, LGBTQ+ and pet friendly. Comfortable private room and breakfast included. Great base for the dunes.',
        pt: 'Hostel com muita vibe, LGBTQ+ e pet friendly. Quarto privado confortável e café incluso. Ótima base para as dunas.',
      },
    },
    {
      id: 'c4',
      name: 'João P.',
      origin: 'BR',
      rating: 5,
      date: '2026-01-22',
      source: 'Google',
      text: {
        es: 'Llegamos de la terminal en 5 minutos a pie. Excelente ubicación, gente buena y el Bora Beer en el hostel es un diferencial.',
        en: 'We walked from the terminal in 5 minutes. Excellent location, nice people, and Bora Beer at the hostel is a plus.',
        pt: 'Chegamos da terminal em 5 minutos a pé. Ótima localização, gente bacana e o Bora Beer no hostel é um diferencial.',
      },
    },
    {
      id: 'c5',
      name: 'Ana & Diego',
      origin: 'AR',
      rating: 5,
      date: '2025-12-30',
      source: 'Google',
      text: {
        es: 'Pasamos Año Nuevo acá. Espacios comunes geniales, cocina completa y cerca de todo. Se nota que es un lugar hecho con cariño.',
        en: 'We spent New Year here. Great common areas, full kitchen and close to everything. You can tell it is run with care.',
        pt: 'Passamos o Ano Novo aqui. Espaços comuns ótimos, cozinha completa e perto de tudo. Dá para ver que é feito com carinho.',
      },
    },
    {
      id: 'c6',
      name: 'Sofía M.',
      origin: 'UY',
      rating: 4,
      date: '2025-11-15',
      source: 'Google',
      text: {
        es: 'Muy buena relación calidad-precio en temporada media. La pileta climatizada en días frescos fue un plus inesperado.',
        en: 'Great value in shoulder season. The heated pool on cooler days was an unexpected plus.',
        pt: 'Ótimo custo-benefício na temporada média. A piscina climatizada em dias frescos foi um plus inesperado.',
      },
    },
    {
      id: 'c7',
      name: 'Tomás H.',
      origin: 'AR',
      rating: 5,
      date: '2025-10-08',
      source: 'Google',
      text: {
        es: 'Desde el hostel caminamos a Cabo Polonio por las dunas: experiencia única. Recepción amable y tips claros para armar el día.',
        en: 'We walked to Cabo Polonio through the dunes from the hostel — unique experience. Friendly reception and clear day-trip tips.',
        pt: 'Do hostel caminhamos até Cabo Polonio pelas dunas: experiência única. Recepção amável e dicas claras para o dia.',
      },
    },
    {
      id: 'c8',
      name: 'Valentina C.',
      origin: 'UY',
      rating: 3,
      date: '2025-09-02',
      source: 'Google',
      text: {
        es: 'La ubicación es excelente y el personal amable. En temporada alta hay más movimiento de noche; si buscás silencio total, pedí habitación más apartada.',
        en: 'Excellent location and friendly staff. In high season nights are livelier — ask for a quieter room if you want total silence.',
        pt: 'A localização é excelente e a equipe amável. Na alta temporada há mais movimento à noite; se quiser silêncio total, peça um quarto mais afastado.',
      },
    },
  ],
}

let remoteContent = null
let remoteLoaded = false

export function getDefaultContent() {
  return structuredClone(DEFAULTS)
}

function deepMerge(base, overlay) {
  if (!overlay || typeof overlay !== 'object') return base
  const out = structuredClone(base)
  for (const [k, v] of Object.entries(overlay)) {
    if (v == null) continue
    if (k === 'curatedReviews' || k === 'blockedDates') {
      out[k] = structuredClone(v)
    } else if (k === 'rateMonths' && typeof v === 'object') {
      out.rateMonths = { ...out.rateMonths }
      for (const [month, row] of Object.entries(v)) {
        out.rateMonths[month] = { ...out.rateMonths[month], ...structuredClone(row) }
      }
    } else if (k === 'googleRating' && typeof v === 'object') {
      out.googleRating = { ...out.googleRating, ...v }
    } else if (k !== 'version') {
      out[k] = v
    }
  }
  return out
}

export function loadLocalContent() {
  try {
    const raw = localStorage.getItem(ADMIN_CONTENT_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function saveLocalContent(content) {
  const payload = {
    ...content,
    version: 1,
    updatedAt: new Date().toISOString(),
  }
  localStorage.setItem(ADMIN_CONTENT_KEY, JSON.stringify(payload))
  return payload
}

export function clearLocalContent() {
  localStorage.removeItem(ADMIN_CONTENT_KEY)
}

export async function loadRemoteContent() {
  if (remoteLoaded) return remoteContent
  remoteLoaded = true
  try {
    const res = await fetch(`/content.json?t=${Date.now()}`, { cache: 'no-store' })
    if (!res.ok) {
      remoteContent = null
      return null
    }
    remoteContent = await res.json()
    return remoteContent
  } catch {
    remoteContent = null
    return null
  }
}

export async function getContent() {
  const base = getDefaultContent()
  const remote = await loadRemoteContent()
  const local = loadLocalContent()
  let merged = base
  if (remote) merged = deepMerge(merged, remote)
  if (local) merged = deepMerge(merged, local)
  return merged
}

export function getContentSync() {
  const base = getDefaultContent()
  const local = loadLocalContent()
  let merged = base
  if (remoteContent) merged = deepMerge(merged, remoteContent)
  if (local) merged = deepMerge(merged, local)
  return merged
}

export async function sha256(text) {
  const data = new TextEncoder().encode(text)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export async function loginAdmin(password) {
  const res = await fetch('/api/admin-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
    cache: 'no-store',
  })
  let data = {}
  try {
    data = await res.json()
  } catch {
    data = {}
  }
  if (!res.ok || !data.ok || !data.token) {
    const err = new Error(data.error || 'Contraseña incorrecta')
    err.status = res.status
    throw err
  }
  sessionStorage.setItem(ADMIN_TOKEN_KEY, data.token)
  sessionStorage.setItem(ADMIN_TOKEN_EXP_KEY, String(data.exp || ''))
  sessionStorage.setItem(ADMIN_SESSION_KEY, '1')
  return data
}

export async function verifyAdminSession() {
  const token = sessionStorage.getItem(ADMIN_TOKEN_KEY)
  const exp = Number(sessionStorage.getItem(ADMIN_TOKEN_EXP_KEY) || 0)
  if (!token) return false
  if (exp && Date.now() > exp) {
    endAdminSession()
    return false
  }
  try {
    const res = await fetch('/api/admin-verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ token }),
      cache: 'no-store',
    })
    if (!res.ok) {
      endAdminSession()
      return false
    }
    const data = await res.json()
    if (!data.ok) {
      endAdminSession()
      return false
    }
    sessionStorage.setItem(ADMIN_SESSION_KEY, '1')
    return true
  } catch {
    // Offline / API down: do not keep a forged client-only session
    endAdminSession()
    return false
  }
}

/** @deprecated Prefer loginAdmin — kept for older imports */
export async function verifyPassword(password) {
  try {
    await loginAdmin(password)
    return true
  } catch {
    return false
  }
}

export async function setPassword() {
  throw new Error('La contraseña se configura con ADMIN_PASSWORD en el servidor (Vercel / .env.local).')
}

export function isAdminSession() {
  return Boolean(sessionStorage.getItem(ADMIN_TOKEN_KEY)) && sessionStorage.getItem(ADMIN_SESSION_KEY) === '1'
}

export function getAdminToken() {
  return sessionStorage.getItem(ADMIN_TOKEN_KEY) || ''
}

export function startAdminSession() {
  // Token is set by loginAdmin; keep flag for UI gating
  if (sessionStorage.getItem(ADMIN_TOKEN_KEY)) {
    sessionStorage.setItem(ADMIN_SESSION_KEY, '1')
  }
}

export function endAdminSession() {
  sessionStorage.removeItem(ADMIN_SESSION_KEY)
  sessionStorage.removeItem(ADMIN_TOKEN_KEY)
  sessionStorage.removeItem(ADMIN_TOKEN_EXP_KEY)
}

export function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const GUEST_REVIEWS_KEY = 'valizas-guest-reviews'

export function loadGuestReviews() {
  try {
    const raw = localStorage.getItem(GUEST_REVIEWS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveGuestReviews(list) {
  localStorage.setItem(GUEST_REVIEWS_KEY, JSON.stringify(list.slice(0, 40)))
}
