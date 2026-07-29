import { clientIp, rateLimited, readJsonBody, safeEqual, signSession } from './_lib/session.js'

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store')
  if (req.method !== 'POST') {
    res.statusCode = 405
    res.end('Method Not Allowed')
    return
  }

  const ip = clientIp(req)
  if (rateLimited(ip)) {
    res.statusCode = 429
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ ok: false, error: 'Demasiados intentos. Probá en 15 minutos.' }))
    return
  }

  const body = await readJsonBody(req)
  const password = body?.password
  const expected = process.env.ADMIN_PASSWORD
  const secret = process.env.ADMIN_SESSION_SECRET || expected

  if (!expected || !secret) {
    res.statusCode = 503
    res.setHeader('Content-Type', 'application/json')
    res.end(
      JSON.stringify({
        ok: false,
        error: 'Admin no configurado. Definí ADMIN_PASSWORD en Vercel.',
      }),
    )
    return
  }

  if (!safeEqual(password, expected)) {
    res.statusCode = 401
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ ok: false, error: 'Contraseña incorrecta' }))
    return
  }

  const session = signSession(secret, 4)
  res.statusCode = 200
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify({ ok: true, token: session.token, exp: session.exp }))
}
