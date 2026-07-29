import { resolve } from 'node:path'
import { defineConfig } from 'vite'

const htmlMap = {
  '/nosotros': '/nosotros.html',
  '/habitaciones': '/habitaciones.html',
  '/experiencias': '/experiencias.html',
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

export default defineConfig({
  plugins: [cleanUrlPlugin()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        nosotros: resolve(__dirname, 'nosotros.html'),
        habitaciones: resolve(__dirname, 'habitaciones.html'),
        experiencias: resolve(__dirname, 'experiencias.html'),
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
})
