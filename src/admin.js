import './style.css'
import {
  getContent,
  getDefaultContent,
  saveLocalContent,
  clearLocalContent,
  downloadJson,
  verifyPassword,
  setPassword,
  isAdminSession,
  startAdminSession,
  endAdminSession,
  loadGuestReviews,
  saveGuestReviews,
} from './contentStore.js'

const MONTHS_ES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]

let draft = null

function $(sel, root = document) {
  return root.querySelector(sel)
}

function show(el, on) {
  if (!el) return
  el.hidden = !on
}

function status(msg, ok = true) {
  const el = $('#admin-status')
  if (!el) return
  el.textContent = msg
  el.dataset.ok = ok ? '1' : '0'
  el.hidden = !msg
}

function renderRatesForm() {
  const wrap = $('#rates-editor')
  if (!wrap || !draft) return
  wrap.innerHTML = Object.entries(draft.rateMonths)
    .map(([m, r]) => {
      const mi = Number(m) - 1
      return `
      <tr data-month="${m}">
        <td>${MONTHS_ES[mi]}</td>
        <td>
          <select data-field="season">
            <option value="alta" ${r.season === 'alta' ? 'selected' : ''}>Alta</option>
            <option value="media" ${r.season === 'media' ? 'selected' : ''}>Media</option>
            <option value="baja" ${r.season === 'baja' ? 'selected' : ''}>Baja</option>
          </select>
        </td>
        <td><input type="number" data-field="suite0" value="${r.suite[0]}" min="0" step="1" />
            <input type="number" data-field="suite1" value="${r.suite[1]}" min="0" step="1" /></td>
        <td><input type="number" data-field="doble0" value="${r.doble[0]}" min="0" step="1" />
            <input type="number" data-field="doble1" value="${r.doble[1]}" min="0" step="1" /></td>
        <td><input type="number" data-field="dorm0" value="${r.dorm[0]}" min="0" step="1" />
            <input type="number" data-field="dorm1" value="${r.dorm[1]}" min="0" step="1" /></td>
      </tr>`
    })
    .join('')
}

function collectRates() {
  const months = {}
  $('#rates-editor')?.querySelectorAll('tr[data-month]').forEach((tr) => {
    const m = tr.dataset.month
    const val = (f) => Number(tr.querySelector(`[data-field="${f}"]`).value)
    months[m] = {
      season: tr.querySelector('[data-field="season"]').value,
      suite: [val('suite0'), val('suite1')],
      doble: [val('doble0'), val('doble1')],
      dorm: [val('dorm0'), val('dorm1')],
    }
  })
  draft.rateMonths = months
}

function renderReviewsEditor() {
  const wrap = $('#reviews-editor')
  if (!wrap || !draft) return
  wrap.innerHTML = draft.curatedReviews
    .map(
      (r, i) => `
    <article class="admin-review-card" data-index="${i}">
      <div class="admin-review-grid">
        <label>Nombre <input data-f="name" value="${escapeAttr(r.name)}" /></label>
        <label>Origen
          <select data-f="origin">
            ${['UY', 'AR', 'BR', 'OT'].map((o) => `<option ${r.origin === o ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
        </label>
        <label>Estrellas
          <select data-f="rating">
            ${[5, 4, 3, 2, 1].map((n) => `<option value="${n}" ${r.rating === n ? 'selected' : ''}>${n}</option>`).join('')}
          </select>
        </label>
        <label>Fecha <input type="date" data-f="date" value="${r.date || ''}" /></label>
        <label>Fuente <input data-f="source" value="${escapeAttr(r.source || 'Google')}" /></label>
      </div>
      <label class="admin-full">Texto ES
        <textarea data-f="text-es" rows="3">${escapeHtml(typeof r.text === 'string' ? r.text : r.text?.es || '')}</textarea>
      </label>
      <label class="admin-full">Texto EN
        <textarea data-f="text-en" rows="2">${escapeHtml(typeof r.text === 'object' ? r.text?.en || '' : '')}</textarea>
      </label>
      <label class="admin-full">Texto PT
        <textarea data-f="text-pt" rows="2">${escapeHtml(typeof r.text === 'object' ? r.text?.pt || '' : '')}</textarea>
      </label>
      <button type="button" class="btn btn-secondary btn-sm" data-del-review="${i}">Eliminar</button>
    </article>`,
    )
    .join('')

  wrap.querySelectorAll('[data-del-review]').forEach((btn) => {
    btn.addEventListener('click', () => {
      collectReviews()
      draft.curatedReviews.splice(Number(btn.dataset.delReview), 1)
      renderReviewsEditor()
    })
  })
}

function collectReviews() {
  const list = []
  $('#reviews-editor')?.querySelectorAll('.admin-review-card').forEach((card, i) => {
    const g = (f) => card.querySelector(`[data-f="${f}"]`)?.value?.trim() || ''
    const prev = draft.curatedReviews[i]
    list.push({
      id: prev?.id || `c-${Date.now()}-${i}`,
      name: g('name') || 'Anónimo',
      origin: g('origin') || 'UY',
      rating: Number(g('rating') || 5),
      date: g('date') || new Date().toISOString().slice(0, 10),
      source: g('source') || 'Google',
      text: { es: g('text-es'), en: g('text-en'), pt: g('text-pt') },
    })
  })
  draft.curatedReviews = list
}

function renderGuestReviews() {
  const wrap = $('#guest-reviews')
  if (!wrap) return
  const guests = loadGuestReviews()
  if (!guests.length) {
    wrap.innerHTML = '<p class="admin-muted">No hay reseñas enviadas desde la web.</p>'
    return
  }
  wrap.innerHTML = guests
    .map(
      (r, i) => `
    <article class="admin-guest-row">
      <div>
        <strong>${escapeHtml(r.name)}</strong> · ${r.rating}★ · ${r.date}
        <p>${escapeHtml(typeof r.text === 'string' ? r.text : '')}</p>
      </div>
      <button type="button" class="btn btn-secondary btn-sm" data-del-guest="${i}">Borrar</button>
    </article>`,
    )
    .join('')

  wrap.querySelectorAll('[data-del-guest]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const list = loadGuestReviews()
      list.splice(Number(btn.dataset.delGuest), 1)
      saveGuestReviews(list)
      renderGuestReviews()
      status('Reseña de huésped eliminada')
    })
  })
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
}

function escapeAttr(s) {
  return String(s).replaceAll('"', '&quot;').replaceAll('<', '&lt;')
}

function fillMeta() {
  $('#usd-uyu').value = draft.usdToUyu
  $('#google-score').value = draft.googleRating.score
  $('#google-count').value = draft.googleRating.reviewCount
  $('#blocked-dates').value = (draft.blockedDates || []).join('\n')
  $('#updated-at').textContent = draft.updatedAt
    ? `Última guardada: ${new Date(draft.updatedAt).toLocaleString('es-UY')}`
    : 'Sin guardar en este navegador'
}

function collectMeta() {
  draft.usdToUyu = Number($('#usd-uyu').value) || 42
  draft.googleRating = {
    score: Number($('#google-score').value) || 4.2,
    reviewCount: Number($('#google-count').value) || 0,
  }
  draft.blockedDates = $('#blocked-dates')
    .value.split(/\n+/)
    .map((s) => s.trim())
    .filter((s) => /^\d{4}-\d{2}-\d{2}$/.test(s))
}

function collectAll() {
  collectMeta()
  collectRates()
  collectReviews()
}

async function openPanel() {
  draft = await getContent()
  show($('#admin-login'), false)
  show($('#admin-app'), true)
  show($('#btn-logout'), true)
  fillMeta()
  renderRatesForm()
  renderReviewsEditor()
  renderGuestReviews()
  status('')
}

function wire() {
  $('#login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault()
    const pass = $('#admin-pass').value
    const ok = await verifyPassword(pass)
    if (!ok) {
      status('Contraseña incorrecta', false)
      return
    }
    startAdminSession()
    await openPanel()
  })

  $('#btn-logout')?.addEventListener('click', () => {
    endAdminSession()
    show($('#admin-app'), false)
    show($('#admin-login'), true)
    show($('#btn-logout'), false)
    status('Sesión cerrada')
  })

  $('#btn-save')?.addEventListener('click', () => {
    collectAll()
    const saved = saveLocalContent(draft)
    draft = saved
    fillMeta()
    status('Guardado en este navegador. El sitio ya usa estos datos acá. Para todos los visitantes: descargá content.json y reemplazalo en public/.')
  })

  $('#btn-export')?.addEventListener('click', () => {
    collectAll()
    downloadJson('content.json', {
      version: 1,
      updatedAt: new Date().toISOString(),
      usdToUyu: draft.usdToUyu,
      blockedDates: draft.blockedDates,
      rateMonths: draft.rateMonths,
      googleRating: draft.googleRating,
      curatedReviews: draft.curatedReviews,
    })
    status('Descargaste content.json — subilo a public/content.json y redesplegá.')
  })

  $('#btn-import')?.addEventListener('click', () => $('#import-file')?.click())

  $('#import-file')?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const json = JSON.parse(await file.text())
      draft = { ...getDefaultContent(), ...json, rateMonths: { ...getDefaultContent().rateMonths, ...json.rateMonths } }
      if (json.curatedReviews) draft.curatedReviews = json.curatedReviews
      if (json.blockedDates) draft.blockedDates = json.blockedDates
      fillMeta()
      renderRatesForm()
      renderReviewsEditor()
      status('JSON importado. Tocá Guardar para aplicarlo en este navegador.')
    } catch {
      status('JSON inválido', false)
    }
    e.target.value = ''
  })

  $('#btn-reset')?.addEventListener('click', async () => {
    if (!confirm('¿Borrar overrides de este navegador y volver a defaults + content.json?')) return
    clearLocalContent()
    draft = await getContent()
    fillMeta()
    renderRatesForm()
    renderReviewsEditor()
    status('Overrides locales borrados')
  })

  $('#btn-add-review')?.addEventListener('click', () => {
    collectReviews()
    draft.curatedReviews.unshift({
      id: `c-${Date.now()}`,
      name: 'Nuevo huésped',
      origin: 'UY',
      rating: 5,
      date: new Date().toISOString().slice(0, 10),
      source: 'Google',
      text: { es: '', en: '', pt: '' },
    })
    renderReviewsEditor()
  })

  $('#password-form')?.addEventListener('submit', async (e) => {
    e.preventDefault()
    const a = $('#new-pass').value
    const b = $('#new-pass2').value
    if (a.length < 4) {
      status('Mínimo 4 caracteres', false)
      return
    }
    if (a !== b) {
      status('Las contraseñas no coinciden', false)
      return
    }
    await setPassword(a)
    $('#new-pass').value = ''
    $('#new-pass2').value = ''
    status('Contraseña actualizada (solo en este navegador)')
  })
}

async function init() {
  wire()
  if (isAdminSession()) await openPanel()
}

init()
