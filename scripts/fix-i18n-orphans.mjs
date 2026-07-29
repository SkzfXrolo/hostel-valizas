import fs from 'fs'

let s = fs.readFileSync('src/i18n.js', 'utf8')

/**
 * Move top-level orphan keys that sit between `},` and the next lang
 * back inside the previous language object.
 */
function absorbOrphansBefore(text, nextLang) {
  const marker = `\n  ${nextLang}: {`
  const idx = text.indexOf(marker)
  if (idx < 0) throw new Error(`missing ${nextLang}`)

  // Walk back from marker to find the preceding `  },` that closed the previous lang too early
  const before = text.slice(0, idx)
  const closeIdx = before.lastIndexOf('\n  },')
  if (closeIdx < 0) throw new Error(`no closing before ${nextLang}`)

  const between = text.slice(closeIdx + '\n  },'.length, idx)
  const orphanLines = between
    .split(/\r?\n/)
    .map((l) => l.trimEnd())
    .filter((l) => l.trim().length > 0)

  if (orphanLines.length === 0) {
    console.log('no orphans before', nextLang)
    return text
  }

  // Validate they look like key lines
  const bad = orphanLines.filter((l) => !/^\s*'[^']+'\s*:/.test(l))
  if (bad.length) {
    throw new Error(`unexpected lines before ${nextLang}: ${bad[0]}`)
  }

  // Ensure last orphan has a trailing comma
  const normalized = orphanLines.map((l, i) => {
    const trimmed = l.replace(/,\s*$/, '') + ','
    // keep 4-space indent inside lang objects
    return '    ' + trimmed.trim()
  })

  const rebuilt =
    text.slice(0, closeIdx) +
    '\n' +
    normalized.join('\n') +
    '\n  },' +
    text.slice(idx)

  console.log('moved', orphanLines.length, 'keys into block before', nextLang)
  return rebuilt
}

s = absorbOrphansBefore(s, 'en')
s = absorbOrphansBefore(s, 'pt')

// Verify: home.ico.pool must appear inside each lang block
function langBlock(src, lang, next) {
  const start = src.indexOf(`\n  ${lang}: {`)
  const end = next ? src.indexOf(`\n  ${next}: {`) : src.indexOf('\n}')
  return src.slice(start, end)
}

const checks = [
  ['es', langBlock(s, 'es', 'en').includes("'home.ico.pool'")],
  ['en', langBlock(s, 'en', 'pt').includes("'home.ico.pool'")],
  ['pt', langBlock(s, 'pt', null).includes("'home.ico.pool'")],
]
checks.forEach(([lang, ok]) => console.log(lang, 'has home.ico.pool:', ok))
if (checks.some(([, ok]) => !ok)) {
  console.error('FIX FAILED')
  process.exit(1)
}

// Ensure no orphan pool between es close and en
const esClose = s.indexOf("\n  en: {")
const gap = s.slice(s.lastIndexOf('\n  },', esClose), esClose)
if (gap.includes("'home.ico.pool'")) {
  console.error('still orphaned before en')
  process.exit(1)
}

fs.writeFileSync('src/i18n.js', s)
console.log('wrote src/i18n.js')
