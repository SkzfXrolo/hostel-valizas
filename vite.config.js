import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'

const DEFAULT_SITE_URL = 'https://hostel-valizas.vercel.app'
import {
  clientIp,
  rateLimited,
  readJsonBody,
  safeEqual,
  signSession,
  verifySession,
} from './api/_lib/session.js'

const htmlMap = {
  '/nosotros': '/nosotros.html',
  '/habitaciones': '/habitaciones.html',
  '/experiencias': '/experiencias.html',
  '/sushi': '/sushi.html',
  '/tarifas': '/tarifas.html',
  '/galeria': '/galeria.html',
  '/resenas': '/resenas.html',
  '/ubicacion': '/ubicacion.html',
  '/faq': '/faq.html',
  '/ficha': '/ficha.html',
  '/admin': '/admin.html',
}

function cleanUrlPlugin() {
  return {
    name: 'clean-urls',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = req.url?.split('?')[0]
        if (url && htmlMap[url]) req.url = htmlMap[url] + (req.url.includes('?') ? '?' + req.url.split('?')[1] : '')
        next()
      })
    },
  }
}

/** Bake final domain into HTML / sitemap / robots at build time. */
function siteUrlPlugin(env) {
  const raw = String(env.VITE_SITE_URL || DEFAULT_SITE_URL)
    .trim()
    .replace(/^VITE_SITE_URL\s*=\s*/i, '')
  const site = raw.replace(/\/$/, '') || DEFAULT_SITE_URL
  const rewrite = (text) => text.replaceAll(DEFAULT_SITE_URL, site)
  return {
    name: 'site-url',
    transformIndexHtml: {
      order: 'pre',
      handler(html) {
        return rewrite(html)
      },
    },
    closeBundle() {
      const dist = resolve(__dirname, 'dist')
      for (const file of ['sitemap.xml', 'robots.txt']) {
        const path = resolve(dist, file)
        if (!existsSync(path)) continue
        writeFileSync(path, rewrite(readFileSync(path, 'utf8')))
      }
    },
  }
}

function adminAuthDevPlugin(env) {
  return {
    name: 'admin-auth-dev',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split('?')[0]
        if (url !== '/api/admin-login' && url !== '/api/admin-verify') return next()

        // Mirror Vercel handlers for local `vite` / `vite preview` with env from .env.local
        process.env.ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || env.ADMIN_PASSWORD
        process.env.ADMIN_SESSION_SECRET =
          process.env.ADMIN_SESSION_SECRET || env.ADMIN_SESSION_SECRET || env.ADMIN_PASSWORD

        res.setHeader('Cache-Control', 'no-store')
        res.setHeader('Content-Type', 'application/json')

        if (url === '/api/admin-login') {
          if (req.method !== 'POST') {
            res.statusCode = 405
            res.end('Method Not Allowed')
            return
          }
          const ip = clientIp(req)
          if (rateLimited(ip)) {
            res.statusCode = 429
            res.end(JSON.stringify({ ok: false, error: 'Demasiados intentos. Probá en 15 minutos.' }))
            return
          }
          const body = await readJsonBody(req)
          const expected = process.env.ADMIN_PASSWORD
          const secret = process.env.ADMIN_SESSION_SECRET || expected
          if (!expected || !secret) {
            res.statusCode = 503
            res.end(
              JSON.stringify({
                ok: false,
                error: 'Admin no configurado. Creá .env.local con ADMIN_PASSWORD.',
              }),
            )
            return
          }
          if (!safeEqual(body?.password, expected)) {
            res.statusCode = 401
            res.end(JSON.stringify({ ok: false, error: 'Contraseña incorrecta' }))
            return
          }
          const session = signSession(secret, 4)
          res.statusCode = 200
          res.end(JSON.stringify({ ok: true, token: session.token, exp: session.exp }))
          return
        }

        if (url === '/api/admin-verify') {
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
            res.end(JSON.stringify({ ok: false }))
            return
          }
          res.statusCode = 200
          res.end(JSON.stringify({ ok: true }))
        }
      })
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [cleanUrlPlugin(), siteUrlPlugin(env), adminAuthDevPlugin(env)],
    build: {
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
          nosotros: resolve(__dirname, 'nosotros.html'),
          habitaciones: resolve(__dirname, 'habitaciones.html'),
          experiencias: resolve(__dirname, 'experiencias.html'),
          sushi: resolve(__dirname, 'sushi.html'),
          tarifas: resolve(__dirname, 'tarifas.html'),
          galeria: resolve(__dirname, 'galeria.html'),
          resenas: resolve(__dirname, 'resenas.html'),
          ubicacion: resolve(__dirname, 'ubicacion.html'),
          faq: resolve(__dirname, 'faq.html'),
          ficha: resolve(__dirname, 'ficha.html'),
          admin: resolve(__dirname, 'admin.html'),
          notfound: resolve(__dirname, '404.html'),
        },
      },
    },
  }
})
