import { t } from './i18n.js'
import { applyTheme } from './theme.js'

const NAV = [
  { href: '/nosotros', key: 'nav.nosotros', id: 'nosotros' },
  { href: '/habitaciones', key: 'nav.habitaciones', id: 'habitaciones' },
  { href: '/experiencias', key: 'nav.experiencias', id: 'experiencias' },
  { href: '/sushi', key: 'nav.sushi', id: 'sushi' },
  // Tarifas oculto de momento — página /tarifas sigue existiendo
  { href: '/resenas', key: 'nav.resenas', id: 'resenas' },
  { href: '/galeria', key: 'nav.galeria', id: 'galeria' },
  { href: '/faq', key: 'nav.faq', id: 'faq' },
  { href: '/ubicacion', key: 'nav.ubicacion', id: 'ubicacion' },
]

const WA_BY_PAGE = {
  home: 'general',
  habitaciones: 'habitaciones',
  tarifas: 'tarifas',
  experiencias: 'dunas',
  sushi: 'sushi',
  galeria: 'general',
  nosotros: 'general',
  resenas: 'general',
  ubicacion: 'ubicacion',
  faq: 'faq',
  ficha: 'general',
  404: '404',
}

function navLinks(activeId) {
  return NAV.map(
    (item) =>
      `<a href="${item.href}" class="${item.id === activeId ? 'is-active' : ''}" data-i18n="${item.key}">${t(item.key)}</a>`,
  ).join('')
}

function langSwitchHtml() {
  return `
    <div class="lang-switch" role="group" aria-label="Language">
      <button type="button" data-lang="es" aria-pressed="true">ES</button>
      <button type="button" data-lang="en" aria-pressed="false">EN</button>
      <button type="button" data-lang="pt" aria-pressed="false">PT</button>
    </div>
  `
}

export function mountShell() {
  const page = document.body.dataset.page || 'home'
  const isHome = page === 'home'
  const waContext = WA_BY_PAGE[page] || 'general'

  const headerHtml = `
    <a class="skip-link" href="#main" data-i18n="skip">${t('skip')}</a>
    <header class="site-header ${isHome ? '' : 'is-scrolled site-header--solid'}" id="header">
      <div class="header-inner">
        <a class="logo" href="/">
          <span class="logo-mark logo-mark--img"><img src="/assets/brand/logo-script.webp" alt="" width="40" height="40" decoding="async" /></span>
          <span class="logo-text">Valizas Hostel</span>
        </a>
        <nav class="nav" data-i18n-aria="nav.aria" aria-label="${t('nav.aria')}">${navLinks(page)}</nav>
        <div class="header-actions">
          <button type="button" class="theme-toggle" data-theme-toggle aria-pressed="false" title="Modo noche">☾</button>
          ${langSwitchHtml()}
          <img
            class="header-rocha"
            src="/assets/brand/rocha-aqui-estas-bien.webp"
            alt="Rocha — aquí estás bien"
            width="72"
            height="68"
            decoding="async"
          />
          <a class="btn btn-primary btn-sm header-cta" data-wa="general" data-wa-context="${waContext}" href="#" data-i18n="cta.reservar">${t('cta.reservar')}</a>
        </div>
        <img
          class="header-rocha header-rocha--mobile"
          src="/assets/brand/rocha-aqui-estas-bien.webp"
          alt="Rocha — aquí estás bien"
          width="56"
          height="54"
          decoding="async"
        />
        <button class="nav-toggle" type="button" data-i18n-aria="cta.menu" aria-label="${t('cta.menu')}" aria-expanded="false">
          <span></span><span></span><span></span>
        </button>
      </div>
      <div class="mobile-nav" hidden>
        <div class="mobile-nav-tools">
          <button type="button" class="theme-toggle" data-theme-toggle aria-pressed="false" title="Modo noche">☾</button>
          ${langSwitchHtml()}
        </div>
        ${navLinks(page)}
        <a class="btn btn-primary" data-wa="general" data-wa-context="${waContext}" href="#" data-i18n="cta.reservarWa">${t('cta.reservarWa')}</a>
      </div>
    </header>
  `

  const footerHtml = `
    <footer class="site-footer">
      <div class="container footer-inner">
        <p>© <span id="year"></span> <span data-i18n="footer.tag">${t('footer.tag')}</span></p>
        <div class="footer-links">
          <a href="/nosotros" data-i18n="nav.nosotros">${t('nav.nosotros')}</a>
          <a href="/habitaciones" data-i18n="nav.habitaciones">${t('nav.habitaciones')}</a>
          <a href="/sushi" data-i18n="nav.sushi">${t('nav.sushi')}</a>
          <a href="/faq" data-i18n="nav.faq">${t('nav.faq')}</a>
          <a href="/ficha">Ficha</a>
          <a href="https://www.instagram.com/hostelvalizas/" target="_blank" rel="noopener">Instagram</a>
          <a href="https://wa.me/59894340425" data-wa-context="${waContext}" target="_blank" rel="noopener">WhatsApp</a>
        </div>
      </div>
    </footer>
    <div class="mobile-dock mobile-dock--5" aria-label="Acciones rápidas">
      <a class="mobile-dock-btn" data-wa="general" data-wa-context="${waContext}" href="#" title="WhatsApp">
        <span aria-hidden="true">✆</span>
        <span>WhatsApp</span>
      </a>
      <a
        class="mobile-dock-btn"
        href="https://www.booking.com/hotel/uy/valizas.html"
        target="_blank"
        rel="noopener noreferrer"
        title="Booking"
      >
        <span aria-hidden="true">Ⓑ</span>
        <span>Booking</span>
      </a>
      <a class="mobile-dock-btn mobile-dock-wa" data-wa="general" data-wa-context="${waContext}" href="#" title="Reservar">
        <span aria-hidden="true">★</span>
        <span data-i18n="cta.reservar">${t('cta.reservar')}</span>
      </a>
      <a
        class="mobile-dock-btn"
        href="https://www.instagram.com/hostelvalizas/"
        target="_blank"
        rel="noopener noreferrer"
        title="Instagram"
      >
        <span aria-hidden="true">◎</span>
        <span>Instagram</span>
      </a>
      <a
        class="mobile-dock-btn"
        href="https://www.facebook.com/hostelvalizas"
        target="_blank"
        rel="noopener noreferrer"
        title="Facebook"
      >
        <span aria-hidden="true">f</span>
        <span>Facebook</span>
      </a>
    </div>
    <a
      class="fab-whatsapp"
      href="https://wa.me/59894340425"
      data-wa="general"
      data-wa-context="${waContext}"
      target="_blank"
      rel="noopener noreferrer"
      data-i18n-aria="fab.aria"
      aria-label="${t('fab.aria')}"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path fill="currentColor" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.435 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
      </svg>
      <span data-i18n="fab.reservas">${t('fab.reservas')}</span>
    </a>
  `

  const headerMount = document.getElementById('site-header')
  const footerMount = document.getElementById('site-footer')
  if (headerMount) {
    headerMount.insertAdjacentHTML('beforebegin', headerHtml)
    headerMount.remove()
  } else {
    document.body.insertAdjacentHTML('afterbegin', headerHtml)
  }
  if (footerMount) {
    footerMount.insertAdjacentHTML('beforebegin', footerHtml)
    footerMount.remove()
  } else {
    document.body.insertAdjacentHTML('beforeend', footerHtml)
  }

  const year = document.getElementById('year')
  if (year) year.textContent = String(new Date().getFullYear())
  applyTheme()
}

export function setupNav() {
  const header = document.getElementById('header')
  const toggle = document.querySelector('.nav-toggle')
  const mobile = document.querySelector('.mobile-nav')
  const isHome = document.body.dataset.page === 'home'

  if (isHome) {
    window.addEventListener(
      'scroll',
      () => {
        header?.classList.toggle('is-scrolled', window.scrollY > 40)
      },
      { passive: true },
    )
  }

  toggle?.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') === 'true'
    toggle.setAttribute('aria-expanded', String(!open))
    if (mobile) mobile.hidden = open
  })

  mobile?.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => {
      mobile.hidden = true
      toggle?.setAttribute('aria-expanded', 'false')
    })
  })
}

let revealIo = null

/** Observe (or re-observe) `.reveal` nodes — safe to call after dynamic re-renders. */
export function setupReveal() {
  if (!revealIo) {
    revealIo = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            revealIo.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
  }

  const vh = window.innerHeight || 0
  document.querySelectorAll('.reveal:not(.is-visible)').forEach((el) => {
    const rect = el.getBoundingClientRect()
    // Already on screen (e.g. after language switch re-render): show immediately
    if (rect.top < vh - 40 && rect.bottom > 12) {
      el.classList.add('is-visible')
      return
    }
    revealIo.observe(el)
  })
}
