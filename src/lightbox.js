/**
 * Lightbox for experience carousel & gallery.
 */
export function setupLightbox() {
  if (document.getElementById('lightbox')) return

  const root = document.createElement('div')
  root.id = 'lightbox'
  root.className = 'lightbox'
  root.hidden = true
  root.innerHTML = `
    <button type="button" class="lightbox-close" aria-label="Cerrar">×</button>
    <button type="button" class="lightbox-nav lightbox-prev" aria-label="Anterior">‹</button>
    <figure class="lightbox-figure">
      <img class="lightbox-img" alt="" />
      <figcaption class="lightbox-caption"></figcaption>
    </figure>
    <button type="button" class="lightbox-nav lightbox-next" aria-label="Siguiente">›</button>
  `
  document.body.appendChild(root)

  const img = root.querySelector('.lightbox-img')
  const caption = root.querySelector('.lightbox-caption')
  let items = []
  let index = 0

  function show(i) {
    index = (i + items.length) % items.length
    const item = items[index]
    img.src = item.src
    img.alt = item.alt || ''
    caption.textContent = item.caption || ''
    root.hidden = false
    document.body.classList.add('lightbox-open')
  }

  function hide() {
    root.hidden = true
    document.body.classList.remove('lightbox-open')
    img.removeAttribute('src')
  }

  root.querySelector('.lightbox-close').addEventListener('click', hide)
  root.querySelector('.lightbox-prev').addEventListener('click', () => show(index - 1))
  root.querySelector('.lightbox-next').addEventListener('click', () => show(index + 1))
  root.addEventListener('click', (e) => {
    if (e.target === root) hide()
  })
  document.addEventListener('keydown', (e) => {
    if (root.hidden) return
    if (e.key === 'Escape') hide()
    if (e.key === 'ArrowLeft') show(index - 1)
    if (e.key === 'ArrowRight') show(index + 1)
  })

  // Gallery items
  document.querySelectorAll('.gallery-item').forEach((el, i, list) => {
    el.addEventListener('click', (e) => {
      e.preventDefault()
      items = [...list].map((node) => {
        const bg = getComputedStyle(node).backgroundImage
        const m = bg.match(/url\(["']?([^"')]+)/)
        return { src: m?.[1] || '', alt: node.getAttribute('aria-label') || 'Foto', caption: '' }
      })
      show(i)
    })
  })

  // Experience slides click
  document.querySelectorAll('.xp-slide .xp-media, .xp-slide').forEach((el) => {
    el.style.cursor = 'zoom-in'
  })
  document.getElementById('experience')?.addEventListener('click', (e) => {
    const slide = e.target.closest('.xp-slide')
    if (!slide || e.target.closest('.xp-controls, .xp-nav, .xp-dot')) return
    const slides = [...document.querySelectorAll('.xp-slide')]
    items = slides.map((s) => {
      const bg = getComputedStyle(s.querySelector('.xp-media') || s).backgroundImage
      const m = bg.match(/url\(["']?([^"')]+)/)
      const title = s.querySelector('h3')?.textContent || ''
      return { src: m?.[1] || '', alt: title, caption: title }
    })
    const i = slides.indexOf(slide)
    if (i >= 0) show(i)
  })
}
