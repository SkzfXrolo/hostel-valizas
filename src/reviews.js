import { t, getLang } from './i18n.js'
import {
  getContentSync,
  loadGuestReviews,
  saveGuestReviews,
  GUEST_REVIEWS_KEY,
  DEFAULTS,
} from './contentStore.js'

export const GOOGLE_RATING = DEFAULTS.googleRating
export { GUEST_REVIEWS_KEY }

function starsHtml(rating) {
  const full = Math.round(rating)
  return Array.from({ length: 5 }, (_, i) => (i < full ? '★' : '☆')).join('')
}

function formatDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  const lang = getLang()
  const locale = lang === 'en' ? 'en-US' : lang === 'pt' ? 'pt-BR' : 'es-UY'
  return new Date(y, m - 1, d).toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function reviewText(review) {
  if (typeof review.text === 'string') return review.text
  const lang = getLang()
  return review.text?.[lang] || review.text?.es || ''
}

function saveGuestReview(review) {
  const list = loadGuestReviews()
  list.unshift(review)
  saveGuestReviews(list)
}

function getCurated() {
  return getContentSync().curatedReviews || DEFAULTS.curatedReviews
}

export function getFeaturedReviews(limit = 6) {
  const all = [...loadGuestReviews(), ...getCurated()]
  const sorted = all.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
  const positive = sorted.filter((r) => r.rating >= 4)
  const mild = sorted.filter((r) => r.rating === 3)
  const picked = [...positive]
  if (mild.length && picked.length < limit) picked.push(mild[0])
  return picked.slice(0, limit)
}

export function renderReviews() {
  const scoreEl = document.getElementById('google-score')
  const countEl = document.getElementById('google-count')
  const starsEl = document.getElementById('google-stars')
  const listEl = document.getElementById('reviews-list')
  const { googleRating } = getContentSync()

  if (scoreEl) scoreEl.textContent = Number(googleRating.score).toFixed(1)
  if (countEl) countEl.textContent = t('reviews.count', { n: googleRating.reviewCount })
  if (starsEl) {
    starsEl.textContent = starsHtml(googleRating.score)
    starsEl.setAttribute('aria-label', `${googleRating.score} / 5`)
  }

  if (!listEl) return

  const limitAttr = parseInt(listEl.dataset.limit || '', 10)
  const limit = Number.isFinite(limitAttr) && limitAttr > 0 ? limitAttr : 6
  const reviews = getFeaturedReviews(limit)
  listEl.innerHTML = reviews
    .map((r) => {
      const origin = r.origin ? `<span class="review-origin">${r.origin}</span>` : ''
      return `
    <article class="review-card reveal">
      <header class="review-card-head">
        <div class="review-avatar" aria-hidden="true">${r.name.charAt(0)}</div>
        <div>
          <strong>${r.name}${origin}</strong>
          <p class="review-meta">${formatDate(r.date)} · ${r.source === 'Web' ? t('reviews.source.web') : r.source}</p>
        </div>
        <span class="review-stars" aria-label="${r.rating}">${starsHtml(r.rating)}</span>
      </header>
      <p class="review-text">${reviewText(r)}</p>
    </article>
  `
    })
    .join('')
}

export function setupReviewForm() {
  const form = document.getElementById('review-form')
  const status = document.getElementById('review-form-status')
  if (!form) return

  form.addEventListener('submit', (e) => {
    e.preventDefault()
    const data = new FormData(form)
    const name = String(data.get('name') || '').trim() || 'Guest'
    const rating = Math.min(5, Math.max(1, parseInt(String(data.get('rating')), 10) || 5))
    const text = String(data.get('text') || '').trim()
    if (text.length < 12) {
      if (status) {
        status.hidden = false
        status.textContent = t('reviews.form.short')
      }
      return
    }

    const today = new Date()
    saveGuestReview({
      id: `g-${Date.now()}`,
      name,
      rating,
      date: today.toISOString().slice(0, 10),
      source: 'Web',
      text,
    })

    form.reset()
    if (status) {
      status.hidden = false
      status.textContent = rating >= 4 ? t('reviews.form.thanks') : t('reviews.form.thanksLow')
    }
    renderReviews()
    document.getElementById('reviews-list')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}
