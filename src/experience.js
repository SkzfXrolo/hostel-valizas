import { siteImages } from './siteImages.js'
import { t } from './i18n.js'

const AUTO_MS = 5500

export function setupExperience() {
  const root = document.getElementById('experience')
  if (!root) return

  const track = root.querySelector('.xp-track')
  const dots = root.querySelector('.xp-dots')
  const counter = root.querySelector('.xp-counter')
  const progress = root.querySelector('.xp-progress-bar')
  const btnPrev = root.querySelector('.xp-prev')
  const btnNext = root.querySelector('.xp-next')
  const stage = root.querySelector('.xp-stage')

  if (!track || !dots) return

  const SLIDES = siteImages.xpGallery || []
  if (!SLIDES.length) return

  let index = 0
  let timer = null
  let progressRaf = null
  let startedAt = 0
  let paused = false
  let touchX = null

  function renderSlides() {
    track.innerHTML = SLIDES.map((slide, i) => {
      return `
        <article class="xp-slide ${i === 0 ? 'is-active' : ''}" data-index="${i}" style="--xp-img: url('${slide.src}')">
          <div class="xp-media" aria-hidden="true"></div>
          <div class="xp-caption">
            <p class="xp-step">${String(i + 1).padStart(2, '0')} / ${String(SLIDES.length).padStart(2, '0')}</p>
            <h3 data-i18n="${slide.titleKey}">${t(slide.titleKey)}</h3>
            <p data-i18n="${slide.textKey}">${t(slide.textKey)}</p>
          </div>
        </article>
      `
    }).join('')

    dots.innerHTML = SLIDES.map(
      (_, i) =>
        `<button type="button" class="xp-dot ${i === 0 ? 'is-active' : ''}" data-goto="${i}" aria-label="Slide ${i + 1}"></button>`,
    ).join('')
  }

  function setActive(next) {
    index = (next + SLIDES.length) % SLIDES.length
    track.querySelectorAll('.xp-slide').forEach((el, i) => {
      el.classList.toggle('is-active', i === index)
    })
    dots.querySelectorAll('.xp-dot').forEach((el, i) => {
      el.classList.toggle('is-active', i === index)
    })
    if (counter) counter.textContent = `${index + 1} / ${SLIDES.length}`
    restartAuto()
  }

  function stopProgress() {
    if (progressRaf) cancelAnimationFrame(progressRaf)
    progressRaf = null
  }

  function tickProgress() {
    if (!progress || paused) return
    const elapsed = Date.now() - startedAt
    const pct = Math.min(100, (elapsed / AUTO_MS) * 100)
    progress.style.width = `${pct}%`
    if (pct < 100) progressRaf = requestAnimationFrame(tickProgress)
  }

  function restartAuto() {
    clearInterval(timer)
    stopProgress()
    if (progress) progress.style.width = '0%'
    startedAt = Date.now()
    tickProgress()
    timer = setInterval(() => {
      if (!paused) setActive(index + 1)
    }, AUTO_MS)
  }

  renderSlides()
  setActive(0)

  btnPrev?.addEventListener('click', () => setActive(index - 1))
  btnNext?.addEventListener('click', () => setActive(index + 1))
  dots.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-goto]')
    if (!btn) return
    setActive(Number(btn.dataset.goto))
  })

  stage?.addEventListener('mouseenter', () => {
    paused = true
    stopProgress()
  })
  stage?.addEventListener('mouseleave', () => {
    paused = false
    restartAuto()
  })

  stage?.addEventListener(
    'touchstart',
    (e) => {
      touchX = e.changedTouches[0].clientX
    },
    { passive: true },
  )
  stage?.addEventListener(
    'touchend',
    (e) => {
      if (touchX == null) return
      const dx = e.changedTouches[0].clientX - touchX
      if (Math.abs(dx) > 40) setActive(index + (dx < 0 ? 1 : -1))
      touchX = null
    },
    { passive: true },
  )

  window.addEventListener('valizas:lang', () => {
    renderSlides()
    setActive(index)
  })
}
