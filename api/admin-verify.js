import { readJsonBody, verifySession } from './_lib/session.js'

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store')
  if (req.method !== 'GET' && req.method !== 'POST') {
    res.statusCode = 405
    res.end('Method Not Allowed')
    return
  }

  const auth = req.headers.authorization || ''
  const headerToken = auth.startsWith('Bearer ') ? auth.slice(7) : ''
  let bodyToken = ''
  if (req.method === 'POST') {
    const body = await readJsonBody(req)
    bodyToken = body?.token || ''
  }
  const token = headerToken || bodyToken
  const secret = process.env.ADMIN_SESSION_SECRET || process.env.ADMIN_PASSWORD

  if (!secret || !verifySession(token, secret)) {
    res.statusCode = 401
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ ok: false }))
    return
  }

  res.statusCode = 200
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify({ ok: true }))
}
