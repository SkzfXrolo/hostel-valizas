import crypto from 'node:crypto'

export function safeEqual(a, b) {
  const aa = Buffer.from(String(a ?? ''), 'utf8')
  const bb = Buffer.from(String(b ?? ''), 'utf8')
  if (aa.length !== bb.length) {
    // burn comparable time
    crypto.timingSafeEqual(aa, Buffer.alloc(aa.length))
    return false
  }
  return crypto.timingSafeEqual(aa, bb)
}

export function signSession(secret, hours = 4) {
  const exp = Date.now() + hours * 60 * 60 * 1000
  const payload = Buffer.from(JSON.stringify({ role: 'admin', exp }), 'utf8').toString('base64url')
  const sig = crypto.createHmac('sha256', secret).update(payload).digest('base64url')
  return { token: `${payload}.${sig}`, exp }
}

export function verifySession(token, secret) {
  if (!token || !secret || typeof token !== 'string') return false
  const [payload, sig] = token.split('.')
  if (!payload || !sig) return false
  const expected = crypto.createHmac('sha256', secret).update(payload).digest('base64url')
  if (!safeEqual(sig, expected)) return false
  try {
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'))
    if (data.role !== 'admin' || typeof data.exp !== 'number') return false
    if (Date.now() > data.exp) return false
    return true
  } catch {
    return false
  }
}

const MAX_ATTEMPTS = 8
const WINDOW_MS = 15 * 60 * 1000
const attempts = new Map()

export function clientIp(req) {
  const xf = req.headers['x-forwarded-for']
  if (typeof xf === 'string' && xf.length) return xf.split(',')[0].trim()
  return req.socket?.remoteAddress || 'unknown'
}

export function rateLimited(ip) {
  const now = Date.now()
  const row = attempts.get(ip) || { count: 0, start: now }
  if (now - row.start > WINDOW_MS) {
    attempts.set(ip, { count: 1, start: now })
    return false
  }
  row.count += 1
  attempts.set(ip, row)
  return row.count > MAX_ATTEMPTS
}

export function readJsonBody(req) {
  return new Promise((resolve) => {
    if (req.body && typeof req.body === 'object') {
      resolve(req.body)
      return
    }
    if (typeof req.body === 'string') {
      try {
        resolve(JSON.parse(req.body))
      } catch {
        resolve({})
      }
      return
    }
    let raw = ''
    req.on('data', (chunk) => {
      raw += chunk
      if (raw.length > 4096) {
        resolve({})
        req.destroy()
      }
    })
    req.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {})
      } catch {
        resolve({})
      }
    })
    req.on('error', () => resolve({}))
  })
}
