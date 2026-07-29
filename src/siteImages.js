/** Imágenes locales — pack WhatsApp dueños + assets existentes */
export const siteImages = {
  logo: '/assets/brand/logo-script.webp',
  heroSlides: [
    '/assets/home/hero-pool.webp',
    '/assets/home/hero-float.webp',
    '/assets/home/hero-lounge.webp',
    '/assets/home/hero-party.webp',
  ],
  heroCover: '/assets/hero-cover.gif',
  heroPoster: '/assets/home/hero-pool.webp',
  owners: {
    duo: '/assets/home/owners.webp',
    duo2: '/assets/home/owners-2.webp',
  },
  location: {
    front: '/assets/home/location-front.webp',
    night: '/assets/home/location-night.webp',
  },
  ideal: {
    camps: '/assets/home/ideal-camps.webp',
    couples: '/assets/home/ideal-couples.webp',
    backpack: '/assets/home/ideal-backpack.webp',
    families: '/assets/home/ideal-families.webp',
    lgbtq: '/assets/home/ideal-lgbtq.webp',
  },
  rochaLgbt: '/assets/home/rocha-lgbt.webp',
  rooms: {
    suite: '/assets/gallery/rooms.webp',
    'doble-privada': '/assets/home/ideal-couples.webp',
    'dorm-4': '/assets/rooms/dorm-4.webp',
    'dorm-6': '/assets/rooms/dorm-6.webp',
    'dorm-8': '/assets/rooms/dorm-8.webp',
    'dorm-12': '/assets/rooms/dorm-12.webp',
  },
  experiences: {
    coliving: '/assets/gallery/coliving.webp',
    bora: '/assets/gallery/bora.webp',
    dunas: '/assets/gallery/dunas.webp',
    disfruta: '/assets/gallery/pool.webp',
    noctilucas: '/assets/gallery/dunas-group.webp',
  },
  gallery: [
    '/assets/gallery/pool.webp',
    '/assets/gallery/heated.webp',
    '/assets/gallery/rooms.webp',
    '/assets/gallery/coliving.webp',
    '/assets/gallery/library.webp',
    '/assets/gallery/bbq-social.webp',
    '/assets/gallery/solarium.webp',
    '/assets/gallery/bora.webp',
    '/assets/gallery/reception.webp',
    '/assets/gallery/terrace.webp',
    '/assets/gallery/night.webp',
    '/assets/gallery/party.webp',
    '/assets/gallery/dunas.webp',
    '/assets/gallery/pool-float.webp',
  ],
  tour: [
    { src: '/assets/gallery/pool.webp', key: 'tour.pool' },
    { src: '/assets/gallery/bora.webp', key: 'tour.bora' },
    { src: '/assets/gallery/dunas.webp', key: 'tour.dunas' },
    { src: '/assets/gallery/rooms.webp', key: 'tour.room' },
    { src: '/assets/gallery/coliving.webp', key: 'tour.vibe' },
  ],
  xpGallery: [
    { src: '/assets/gallery/pool.webp', titleKey: 'exp.g.pool', textKey: 'exp.g.poolT' },
    { src: '/assets/gallery/heated.webp', titleKey: 'exp.g.heated', textKey: 'exp.g.heatedT' },
    { src: '/assets/gallery/rooms.webp', titleKey: 'exp.g.rooms', textKey: 'exp.g.roomsT' },
    { src: '/assets/gallery/coliving.webp', titleKey: 'exp.g.coliving', textKey: 'exp.g.colivingT' },
    { src: '/assets/gallery/library.webp', titleKey: 'exp.g.library', textKey: 'exp.g.libraryT' },
    { src: '/assets/gallery/bbq-social.webp', titleKey: 'exp.g.bbq', textKey: 'exp.g.bbqT' },
    { src: '/assets/gallery/solarium.webp', titleKey: 'exp.g.solarium', textKey: 'exp.g.solariumT' },
    { src: '/assets/gallery/bora.webp', titleKey: 'exp.g.bora', textKey: 'exp.g.boraT' },
    { src: '/assets/gallery/reception.webp', titleKey: 'exp.g.reception', textKey: 'exp.g.receptionT' },
    { src: '/assets/gallery/terrace.webp', titleKey: 'exp.g.terrace', textKey: 'exp.g.terraceT' },
    { src: '/assets/gallery/night.webp', titleKey: 'exp.g.night', textKey: 'exp.g.nightT' },
    { src: '/assets/gallery/party.webp', titleKey: 'exp.g.party', textKey: 'exp.g.partyT' },
    { src: '/assets/gallery/dunas.webp', titleKey: 'exp.g.dunas', textKey: 'exp.g.dunasT' },
    { src: '/assets/gallery/pool-float.webp', titleKey: 'exp.g.summer', textKey: 'exp.g.summerT' },
  ],
}

const heroGradient = `linear-gradient(
  165deg,
  rgba(15, 51, 64, 0.12) 0%,
  rgba(15, 51, 64, 0.28) 48%,
  rgba(15, 51, 64, 0.58) 100%
)`

function uniquePaths(paths) {
  return [...new Set(paths.filter(Boolean))]
}

export function applySiteImages() {
  const logoMark = document.querySelector('.logo-mark')
  if (logoMark && siteImages.logo) {
    logoMark.innerHTML = `<img src="${siteImages.logo}" alt="" width="38" height="38" decoding="async" />`
    logoMark.classList.add('logo-mark--img')
  }

  const cover = document.querySelector('.hero-carousel-cover')
  if (cover) cover.remove()

  const video = document.querySelector('.hero-video')
  if (video) video.remove()

  Object.entries(siteImages.experiences).forEach(([key, src]) => {
    const map = {
      coliving: '.exp-img--coliving',
      bora: '.exp-img--bora',
      dunas: '.exp-img--dunas',
      noctilucas: '.exp-img--noctilucas',
    }
    const sel = map[key]
    if (!sel) return
    document.querySelectorAll(sel).forEach((el) => {
      el.style.backgroundImage = `url('${src}')`
    })
  })

  siteImages.gallery.forEach((src, i) => {
    const el = document.querySelector(`.gallery-item.g${i + 1}`)
    if (el) el.style.backgroundImage = `url('${src}')`
  })

  Object.entries(siteImages.owners || {}).forEach(([key, src]) => {
    document.querySelectorAll(`[data-owner="${key}"]`).forEach((img) => {
      img.src = src
      img.loading = 'lazy'
      img.decoding = 'async'
    })
  })

  Object.entries(siteImages.ideal || {}).forEach(([key, src]) => {
    document.querySelectorAll(`[data-ideal="${key}"]`).forEach((el) => {
      el.style.backgroundImage = `url('${src}')`
    })
  })

  Object.entries(siteImages.location || {}).forEach(([key, src]) => {
    document.querySelectorAll(`[data-location="${key}"]`).forEach((el) => {
      if (el.tagName === 'IMG') el.src = src
      else el.style.backgroundImage = `url('${src}')`
    })
  })

  const rocha = document.querySelector('[data-rocha-lgbt]')
  if (rocha && siteImages.rochaLgbt) {
    if (rocha.tagName === 'IMG') rocha.src = siteImages.rochaLgbt
    else rocha.style.backgroundImage = `url('${siteImages.rochaLgbt}')`
  }

  const tour = document.getElementById('space-tour')
  if (tour) {
    tour.innerHTML = siteImages.tour
      .map(
        (item) => `
      <figure class="tour-card reveal">
        <div class="tour-img" style="background-image:url('${item.src}')"></div>
        <figcaption data-i18n="${item.key}">${item.key}</figcaption>
      </figure>`,
      )
      .join('')
  }

  const igGrid = document.getElementById('ig-grid')
  if (igGrid) {
    const igImages = siteImages.gallery.slice(0, 6)
    igGrid.innerHTML = igImages
      .map(
        (src, i) =>
          `<a href="https://www.instagram.com/hostelvalizas/" target="_blank" rel="noopener noreferrer" style="background-image:url('${src}')" aria-label="Instagram ${i + 1}"></a>`,
      )
      .join('')
  }
}

export function roomImageUrl(roomId) {
  return siteImages.rooms[roomId] || siteImages.gallery[0]
}

export function setupHeroCarousel(intervalMs = 5500) {
  const slideEl = document.querySelector('.hero-slide')
  const slides = uniquePaths(siteImages.heroSlides)
  if (!slideEl || slides.length === 0) return

  let index = 0
  const setSlide = (i) => {
    slideEl.style.backgroundImage = `${heroGradient}, url('${slides[i]}')`
  }

  setSlide(0)
  slideEl.classList.add('hero-slide--active')

  if (slides.length < 2) return

  setInterval(() => {
    index = (index + 1) % slides.length
    slideEl.classList.remove('hero-slide--active')
    void slideEl.offsetWidth
    setSlide(index)
    slideEl.classList.add('hero-slide--active')
  }, intervalMs)
}

export function webp(path) {
  return path.replace(/\.(jpe?g|png)$/i, '.webp')
}
