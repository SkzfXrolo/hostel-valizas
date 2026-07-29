import fs from 'fs'

const files = [
  'index.html',
  'tarifas.html',
  'resenas.html',
  'nosotros.html',
  'faq.html',
  '404.html',
  'galeria.html',
  'habitaciones.html',
  'experiencias.html',
  'ubicacion.html',
]

for (const file of files) {
  let t = fs.readFileSync(file, 'utf8')

  // Broken leftovers from over-eager mojibake replacement
  t = t.replaceAll('""', '—')
  t = t.replace(/\u201C\u201D/g, '—')
  t = t.replace(/"\u201D/g, '—')
  t = t.replace(/"\u00A6/g, '…')
  t = t.replace(/"¦/g, '…')
  t = t.replace(/â‰ˆ/g, '≈')
  t = t.replace(/≈/g, '≈')

  if (file === 'index.html') {
    t = t.replace(
      /content="Valizas Hostel Boutique & Suites[^"]*"/,
      'content="Valizas Hostel Boutique & Suites — Barra de Valizas, a 100 m del mar. Reservá por WhatsApp."',
    )
    t = t.replace(
      /(class="xp-nav xp-prev"[^>]*>)[^<]+/,
      '$1‹',
    )
    t = t.replace(
      /(class="xp-nav xp-next"[^>]*>)[^<]+/,
      '$1›',
    )
    t = t.replace(
      /vivir Valizas como un local[^.]+\./,
      'vivir Valizas como un local — todo el año.',
    )
  }

  if (file === 'tarifas.html') {
    t = t.replace(/(id="cal-prev"[^>]*>)[^<]+/, '$1‹')
    t = t.replace(/(id="cal-next"[^>]*>)[^<]+/, '$1›')
    t = t.replace(/1 USD [^0-9]+ 42/, '1 USD ≈ 42')
  }

  if (file === 'resenas.html') {
    t = t.replace(/([1-5]) — /g, '$1 — ')
    t = t.replace(
      /placeholder="[^"]*"/,
      'placeholder="¿Qué te gustó del hostel…?"',
    )
    // rating options
    t = t.replace(/>5 — Excelente</, '>5 — Excelente<')
    t = t.replace(/>5[^<]*Excelente</, '>5 — Excelente<')
    t = t.replace(/>4[^<]*Muy bueno</, '>4 — Muy bueno<')
    t = t.replace(/>3[^<]*Bien</, '>3 — Bien<')
    t = t.replace(/>2[^<]*Regular</, '>2 — Regular<')
    t = t.replace(/>1[^<]*Malo</, '>1 — Malo<')
  }

  fs.writeFileSync(file, t, 'utf8')
  console.log('cleaned', file)
}

// verify no broken attr quotes in meta content
const idx = fs.readFileSync('index.html', 'utf8')
const m = idx.match(/name="description"[\s\S]*?content="([^"]*)"/)
console.log('meta ok?', Boolean(m), m?.[1]?.slice(0, 80))
