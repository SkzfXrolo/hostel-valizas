import './style.css'
import { mountShell, setupNav, setupReveal } from './shell.js'
import { applySiteImages, roomImageUrl, setupHeroCarousel } from './siteImages.js'
import { renderReviews, setupReviewForm } from './reviews.js'
import { t, getLang, setupLangSwitcher, applyI18n } from './i18n.js'
import { setupExperience } from './experience.js'
import { setupLightbox } from './lightbox.js'
import { setupTheme } from './theme.js'
import { setupAnalytics } from './analytics.js'
import { setupSeo } from './seo.js'
import { isBlocked, getUsdToUyu, renderRatesTable } from './rates.js'
import { loadRemoteContent } from './contentStore.js'

const WA_NUMBER = '59894340425'

const WA_CONTEXT_MSGS = {
  general: () => t('wa.hello'),
  habitaciones: () => t('wa.ctx.rooms'),
  tarifas: () => t('wa.ctx.rates'),
  dunas: () => t('wa.ctx.dunas'),
  ubicacion: () => t('wa.ctx.location'),
  faq: () => t('wa.ctx.faq'),
  404: () => t('wa.ctx.lost'),
}

const ROOMS = [
  { id: 'Hab_priv', key: 'habPriv', type: 'privada', tag: true, features: 3, capacity: 2, priceBucket: 'suite' },
  { id: 'Hab_Dob', key: 'habDob', type: 'privada', features: 3, capacity: 2, priceBucket: 'suite' },
  { id: 'Hab_Fam', key: 'habFam', type: 'privada', features: 3, capacity: 4, priceBucket: 'suite' },
  { id: 'Apart_suite_4', key: 'apartSuite4', type: 'privada', tag: true, features: 4, capacity: 4, priceBucket: 'suite' },
  { id: 'Hab_Priv_2', key: 'habPriv2', type: 'privada', features: 3, capacity: 2, priceBucket: 'doble' },
  { id: 'Hab_Dob_Priv', key: 'habDobPriv', type: 'privada', features: 2, capacity: 2, priceBucket: 'doble' },
  { id: 'Hab_Dob_Priv_2', key: 'habDobPriv2', type: 'privada', features: 2, capacity: 2, priceBucket: 'doble' },
  { id: 'Hab_4', key: 'hab4', type: 'compartida', features: 3, capacity: 4, priceBucket: 'dorm' },
  { id: 'Hab_Comp_6', key: 'habComp6', type: 'compartida', features: 3, capacity: 6, priceBucket: 'dorm' },
  { id: 'Hab_Comp_8', key: 'habComp8', type: 'compartida', features: 4, capacity: 8, priceBucket: 'dorm' },
]

const PRICE_TABLE = {
  Hab_priv: { alta: [110, 130], media: [80, 100], baja: [60, 80] },
  Hab_Dob: { alta: [100, 125], media: [75, 95], baja: [58, 78] },
  Hab_Fam: { alta: [130, 160], media: [95, 125], baja: [75, 100] },
  Apart_suite_4: { alta: [140, 180], media: [110, 140], baja: [85, 115] },
  Hab_Priv_2: { alta: [90, 115], media: [70, 95], baja: [50, 72] },
  Hab_Dob_Priv: { alta: [85, 110], media: [65, 90], baja: [48, 70] },
  Hab_Dob_Priv_2: { alta: [85, 110], media: [65, 90], baja: [48, 70] },
  Hab_4: { alta: [30, 40], media: [22, 30], baja: [16, 24] },
  Hab_Comp_6: { alta: [28, 38], media: [20, 28], baja: [15, 22] },
  Hab_Comp_8: { alta: [26, 36], media: [18, 26], baja: [14, 20] },
}

function dateLocale() {
  const lang = getLang()
  if (lang === 'en') return 'en-US'
  if (lang === 'pt') return 'pt-BR'
  return 'es-UY'
}

function getSeason(date) {
  const m = date.getMonth() + 1
  const d = date.getDate()
  if (m === 12 && d >= 15) return 'alta'
  if (m === 1 || m === 2) return 'alta'
  if (m === 7) return 'media'
  if (m === 3 || m === 4 || m === 11) return 'media'
  if (m === 12 && d < 15) return 'media'
  return 'baja'
}

function isWeekend(date) {
  const day = date.getDay()
  return day === 5 || day === 6 || day === 0
}

function formatDateISO(date) {
  return date.toISOString().slice(0, 10)
}

function formatDateHuman(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(dateLocale(), {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

function buildWhatsAppUrl(message) {
  return `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(message)}`
}

function waMessage({ checkIn, checkOut, guests, season, roomHint, name, note, context }) {
  let text = context && WA_CONTEXT_MSGS[context] ? WA_CONTEXT_MSGS[context]() : t('wa.hello')
  if (name) text += ` ${t('wa.name', { name })}`
  if (checkIn && checkOut) {
    text += t('wa.dates', { in: formatDateHuman(checkIn), out: formatDateHuman(checkOut) })
  }
  if (guests) text += t('wa.guests', { n: guests })
  if (season) text += t('wa.ref', { season: t(`season.${season}`) })
  if (roomHint) text += t('wa.room', { room: roomHint })
  if (note) text += ` ${t('wa.note', { note })}`
  if (!context || context === 'general' || context === 'tarifas') text += t('wa.thanks')
  return text
}

function roomName(room) {
  return t(`room.${room.key}.name`)
}

function renderRooms() {
  const grid = document.getElementById('rooms-grid')
  if (!grid) return

  const limit = parseInt(grid.dataset.limit || '', 10)
  const list = Number.isFinite(limit) && limit > 0 ? ROOMS.slice(0, limit) : ROOMS

  grid.innerHTML = list
    .map((room) => {
      const features = Array.from({ length: room.features }, (_, i) => t(`room.${room.key}.f${i + 1}`))
      return `
    <article class="room-card reveal" data-room="${room.id}">
      <div class="room-visual" style="background-image: url('${roomImageUrl(room.id)}')">
        ${room.tag ? `<span class="room-tag">${t(`room.${room.key}.tag`)}</span>` : ''}
        <span class="room-type">${room.type === 'privada' ? t('room.type.private') : t('room.type.shared')}</span>
      </div>
      <div class="room-body">
        <h3>${roomName(room)}</h3>
        <p class="room-meta">${t(`room.${room.key}.beds`)} · ${t(`room.${room.key}.bath`)}</p>
        <p>${t(`room.${room.key}.desc`)}</p>
        <ul class="room-features">
          ${features.map((f) => `<li>${f}</li>`).join('')}
        </ul>
        <div class="room-actions">
          <a class="btn btn-secondary btn-sm" data-wa-room="${room.id}" href="#">${t('room.ask')}</a>
        </div>
      </div>
    </article>
  `
    })
    .join('')

  grid.querySelectorAll('[data-wa-room]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault()
      const id = btn.getAttribute('data-wa-room')
      const room = ROOMS.find((r) => r.id === id)
      window.open(
        buildWhatsAppUrl(waMessage({ roomHint: room ? roomName(room) : '' })),
        '_blank',
        'noopener',
      )
    })
  })
}

function dominantSeason(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 'media'
  const start = new Date(checkIn + 'T12:00:00')
  const end = new Date(checkOut + 'T12:00:00')
  if (end <= start) return 'media'
  const counts = { alta: 0, media: 0, baja: 0 }
  const cur = new Date(start)
  while (cur < end) {
    counts[getSeason(cur)]++
    cur.setDate(cur.getDate() + 1)
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
}

function estimateRange(season, guests, roomId) {
  const g = Math.min(Math.max(parseInt(guests, 10) || 2, 1), 8)
  let key = roomId || 'Hab_Comp_6'
  if (!PRICE_TABLE[key]) {
    key = 'Hab_Comp_6'
    if (g <= 2) key = 'Hab_Dob_Priv'
    if (g >= 4) key = 'Hab_4'
  }
  const table = PRICE_TABLE[key][season] || PRICE_TABLE.Hab_Comp_6[season]
  let [lo, hi] = table
  const room = ROOMS.find((r) => r.id === key)
  if (room?.priceBucket === 'dorm') {
    lo *= g
    hi *= g
  }
  return { lo: Math.round(lo), hi: Math.round(hi), key }
}

function setupPricing() {
  const form = document.getElementById('date-form')
  if (!form) return

  const result = document.getElementById('pricing-result')
  const resultSeason = document.getElementById('result-season')
  const resultRange = document.getElementById('result-range')
  const resultUyu = document.getElementById('result-uyu')
  const resultWa = document.getElementById('result-wa')
  const checkIn = document.getElementById('check-in')
  const checkOut = document.getElementById('check-out')
  const guests = document.getElementById('guests')
  const roomType = document.getElementById('room-type')

  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const dayAfter = new Date(today)
  dayAfter.setDate(dayAfter.getDate() + 3)

  if (checkIn) {
    checkIn.min = formatDateISO(today)
    checkIn.value = formatDateISO(tomorrow)
  }
  if (checkOut) {
    checkOut.min = formatDateISO(tomorrow)
    checkOut.value = formatDateISO(dayAfter)
  }

  checkIn?.addEventListener('change', () => {
    if (checkOut && checkIn.value) {
      checkOut.min = checkIn.value
      if (checkOut.value <= checkIn.value) {
        const next = new Date(checkIn.value + 'T12:00:00')
        next.setDate(next.getDate() + 1)
        checkOut.value = formatDateISO(next)
      }
    }
  })

  function updateResult() {
    if (isBlocked(checkIn?.value) || isBlocked(checkOut?.value)) {
      resultSeason.textContent = t('pricing.blockedWarn')
      resultRange.textContent = ''
      if (resultUyu) resultUyu.textContent = ''
      result.hidden = false
      return
    }

    const season = dominantSeason(checkIn?.value, checkOut?.value)
    const roomId = roomType?.value
    const room = ROOMS.find((r) => r.id === roomId)
    const { lo, hi } = estimateRange(season, guests?.value, roomId)
    const start = checkIn?.value ? new Date(checkIn.value + 'T12:00:00') : null
    const weekendNote = start && isWeekend(start) ? t('season.weekend') : ''
    const name = document.getElementById('quote-name')?.value
    const note = document.getElementById('quote-note')?.value

    resultSeason.textContent = t(`season.${season}`) + weekendNote
    resultRange.textContent = t('pricing.range', { lo, hi })
    if (resultUyu) {
      const fx = getUsdToUyu()
      resultUyu.textContent = t('pricing.uyu', {
        lo: Math.round(lo * fx),
        hi: Math.round(hi * fx),
        rate: fx,
      })
    }
    const msg = waMessage({
      checkIn: checkIn?.value,
      checkOut: checkOut?.value,
      guests: guests?.value,
      season,
      roomHint: room ? roomName(room) : roomId,
      name,
      note,
      context: 'tarifas',
    })
    resultWa.href = buildWhatsAppUrl(msg)
    result.hidden = false
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault()
    updateResult()
    result?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })

  guests?.addEventListener('change', () => {
    if (result && !result.hidden) updateResult()
  })
  roomType?.addEventListener('change', () => {
    if (result && !result.hidden) updateResult()
  })
}

let calYear
let calMonth

function monthNames() {
  const locale = dateLocale()
  return Array.from({ length: 12 }, (_, i) =>
    new Date(2024, i, 1).toLocaleDateString(locale, { month: 'long' }),
  )
}

function weekdayShort() {
  const locale = dateLocale()
  return [1, 2, 3, 4, 5, 6, 7].map((d) =>
    new Date(2024, 0, d).toLocaleDateString(locale, { weekday: 'short' }),
  )
}

function renderCalendar() {
  const cal = document.getElementById('calendar')
  const title = document.getElementById('cal-title')
  if (!cal || !title) return

  const names = monthNames()
  title.textContent = `${names[calMonth]} ${calYear}`

  const first = new Date(calYear, calMonth, 1)
  const startPad = (first.getDay() + 6) % 7
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate()
  const weekdays = weekdayShort()
  let html = weekdays.map((d) => `<div class="cal-wd">${d}</div>`).join('')

  for (let i = 0; i < startPad; i++) html += `<div class="cal-day cal-day--empty"></div>`

  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(calYear, calMonth, day)
    const season = getSeason(date)
    const iso = formatDateISO(date)
    const blocked = isBlocked(iso)
    html += `<button type="button" class="cal-day cal-day--${season}${blocked ? ' cal-day--blocked' : ''}" data-day="${day}" ${blocked ? 'disabled' : ''} title="${blocked ? t('pricing.blocked') : t(`season.${season}`)}">${day}</button>`
  }

  cal.innerHTML = html

  cal.querySelectorAll('.cal-day[data-day]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const day = btn.getAttribute('data-day')
      const iso = formatDateISO(new Date(calYear, calMonth, parseInt(day, 10)))
      const checkIn = document.getElementById('check-in')
      const checkOut = document.getElementById('check-out')
      const selectingOut = checkIn?.value && (!checkOut?.value || iso > checkIn.value)
      if (!selectingOut || iso <= checkIn.value) {
        checkIn.value = iso
        const out = new Date(iso + 'T12:00:00')
        out.setDate(out.getDate() + 2)
        if (checkOut) checkOut.value = formatDateISO(out)
      } else if (checkOut) {
        checkOut.value = iso
      }
      document.getElementById('date-form')?.requestSubmit()
    })
  })
}

function setupCalendar() {
  if (!document.getElementById('calendar')) return
  const now = new Date()
  calYear = now.getFullYear()
  calMonth = now.getMonth()

  document.getElementById('cal-prev')?.addEventListener('click', () => {
    calMonth--
    if (calMonth < 0) {
      calMonth = 11
      calYear--
    }
    renderCalendar()
  })
  document.getElementById('cal-next')?.addEventListener('click', () => {
    calMonth++
    if (calMonth > 11) {
      calMonth = 0
      calYear++
    }
    renderCalendar()
  })

  renderCalendar()
}

function setupWhatsAppLinks() {
  document.querySelectorAll('[data-wa]').forEach((el) => {
    el.addEventListener('click', (e) => {
      if (el.id === 'result-wa' && el.href?.includes('wa.me')) return
      e.preventDefault()
      const context = el.getAttribute('data-wa-context') || 'general'
      const checkIn = document.getElementById('check-in')?.value
      const checkOut = document.getElementById('check-out')?.value
      const guests = document.getElementById('guests')?.value
      const roomType = document.getElementById('room-type')?.value
      const room = ROOMS.find((r) => r.id === roomType)
      window.open(
        buildWhatsAppUrl(
          waMessage({
            checkIn,
            checkOut,
            guests,
            roomHint: room ? roomName(room) : undefined,
            context,
          }),
        ),
        '_blank',
        'noopener',
      )
    })
  })
}

function refreshDynamic() {
  renderRooms()
  if (document.getElementById('calendar')) renderCalendar()
  renderReviews()
  renderRatesTable(document.getElementById('rates-table'), t)
  applyI18n()
  // New `.reveal` nodes start invisible; re-bind observer after lang/content refresh
  setupReveal()
}

async function boot() {
  await loadRemoteContent()
  mountShell()
  setupSeo()
  setupNav()
  setupLangSwitcher()
  setupTheme()
  setupAnalytics()
  applySiteImages()
  setupHeroCarousel()
  renderRooms()
  setupPricing()
  setupCalendar()
  setupWhatsAppLinks()
  renderReviews()
  setupReviewForm()
  setupExperience()
  setupLightbox()
  renderRatesTable(document.getElementById('rates-table'), t)
  setupReveal()
  applyI18n()
}

boot()

window.addEventListener('valizas:lang', () => {
  refreshDynamic()
})
