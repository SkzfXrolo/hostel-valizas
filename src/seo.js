import { getSiteUrl } from './siteConfig.js'

const PAGE_META = {
  home: {
    title: 'Valizas Hostel | Barra de Valizas',
    description:
      'Hostel boutique a 100 m del mar en Barra de Valizas, Rocha. Habitaciones, dormis, pileta y reservas por WhatsApp.',
  },
  nosotros: {
    title: 'Nosotros | Valizas Hostel',
    description: 'Conocé a los anfitriones de Valizas Hostel Boutique en Barra de Valizas.',
  },
  habitaciones: {
    title: 'Habitaciones | Valizas Hostel',
    description: 'Habitaciones, dobles privadas y dormis de 4 a 12 camas. Desayuno incluido.',
  },
  experiencias: {
    title: 'Experiencias | Valizas Hostel',
    description: 'Pileta, Bora Beer, dunas y Cabo Polonio desde Valizas Hostel.',
  },
  sushi: {
    title: 'Sushi Valizas | Come rico, come local',
    description:
      'Sushi Valizas — nigiri, rolls y hot rolls en Barra de Valizas. 10% de descuento para huéspedes del hostel.',
  },
  tarifas: {
    title: 'Tarifas | Valizas Hostel',
    description: 'Tarifas orientativas por temporada y cotización por WhatsApp.',
  },
  galeria: {
    title: 'Galería | Valizas Hostel',
    description: 'Fotos del hostel, la playa y la vida en Barra de Valizas.',
  },
  resenas: {
    title: 'Reseñas | Valizas Hostel',
    description: 'Opiniones de huéspedes y valoración en Google de Valizas Hostel.',
  },
  ubicacion: {
    title: 'Ubicación | Valizas Hostel',
    description: 'Aladino Veiga s/n, Barra de Valizas. Playa a 100 m, terminal a ~300 m.',
  },
  faq: {
    title: 'FAQ | Valizas Hostel',
    description: 'Check-in, mascotas, desayuno, estacionamiento y cómo llegar desde Montevideo.',
  },
  ficha: {
    title: 'Ficha del hostel | Valizas Hostel',
    description: 'Ficha imprimible con datos de contacto y servicios de Valizas Hostel.',
  },
  404: {
    title: 'Página no encontrada | Valizas Hostel',
    description: 'No encontramos esta página. Volvé al inicio o escribinos por WhatsApp.',
  },
}

function upsertMeta(attr, key, content) {
  if (!content) return
  let el = document.head.querySelector(`meta[${attr}="${key}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function upsertLink(rel, href) {
  let el = document.head.querySelector(`link[rel="${rel}"]`)
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', rel)
    document.head.appendChild(el)
  }
  el.setAttribute('href', href)
}

export function setupSeo() {
  const SITE = getSiteUrl()
  const OG_IMAGE = `${SITE}/assets/home/hero-pool.webp`
  const page = document.body.dataset.page || 'home'
  const meta = PAGE_META[page] || PAGE_META.home
  const path = page === 'home' ? '/' : `/${page === '404' ? '' : page}`
  const url = page === '404' ? `${SITE}/` : `${SITE}${path === '/' ? '/' : path}`

  document.title = meta.title
  upsertMeta('name', 'description', meta.description)
  upsertMeta('property', 'og:type', 'website')
  upsertMeta('property', 'og:site_name', 'Valizas Hostel')
  upsertMeta('property', 'og:title', meta.title)
  upsertMeta('property', 'og:description', meta.description)
  upsertMeta('property', 'og:url', url)
  upsertMeta('property', 'og:image', OG_IMAGE)
  upsertMeta('name', 'twitter:card', 'summary_large_image')
  upsertMeta('name', 'twitter:title', meta.title)
  upsertMeta('name', 'twitter:description', meta.description)
  upsertMeta('name', 'twitter:image', OG_IMAGE)
  upsertLink('canonical', url)

  document.querySelectorAll('[data-site-url]').forEach((el) => {
    el.textContent = SITE
  })

  if (page === 'home' && !document.getElementById('hotel-schema')) {
    const script = document.createElement('script')
    script.type = 'application/ld+json'
    script.id = 'hotel-schema'
    script.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'Hostel',
      name: 'Valizas Hostel Boutique',
      description: meta.description,
      url: SITE,
      image: OG_IMAGE,
      telephone: '+59894340425',
      email: 'hostelvalizas@hotmail.com',
      address: {
        '@type': 'PostalAddress',
        streetAddress: 'Aladino Veiga s/n',
        addressLocality: 'Barra de Valizas',
        addressRegion: 'Rocha',
        addressCountry: 'UY',
      },
      geo: {
        '@type': 'GeoCoordinates',
        latitude: -34.337,
        longitude: -53.793,
      },
      sameAs: ['https://www.instagram.com/hostelvalizas/'],
      petsAllowed: true,
      starRating: { '@type': 'Rating', ratingValue: '4.2' },
      checkinTime: '13:00',
      checkoutTime: '10:00',
    })
    document.head.appendChild(script)
  }

  if (page === 'home') {
    const preload = document.createElement('link')
    preload.rel = 'preload'
    preload.as = 'image'
    preload.href = '/assets/hero-1.webp'
    preload.setAttribute('fetchpriority', 'high')
    document.head.appendChild(preload)
  }
}
