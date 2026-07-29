import fs from 'fs'

const files = fs.readdirSync('.').filter((f) => f.endsWith('.html'))

const pairs = [
  ['Ã¡', 'á'],
  ['Ã©', 'é'],
  ['Ã­', 'í'],
  ['Ã³', 'ó'],
  ['Ãº', 'ú'],
  ['Ã±', 'ñ'],
  ['Ã‘', 'Ñ'],
  ['Ã¼', 'ü'],
  ['Ã¡', 'á'],
  ['Â¿', '¿'],
  ['Â¡', '¡'],
  ['Â·', '·'],
  ['Â ', ' '],
  ['â€™', "'"],
  ['â€œ', '"'],
  ['â€', '"'],
  ['â€"', '—'],
  ['â€“', '–'],
  ['â€¦', '…'],
  ['â˜…', '★'],
  ['â˜†', '☆'],
  ['â€¹', '‹'],
  ['â€º', '›'],
  ['â†’', '→'],
  ['Ã“', 'Ó'],
  ['Ã‰', 'É'],
  ['Ã', 'Á'],
]

for (const file of files) {
  let text = fs.readFileSync(file, 'utf8')
  const before = text
  for (const [a, b] of pairs) text = text.split(a).join(b)
  // leftover double-encoding scraps
  text = text.replace(/Ã¡/g, 'á')
  if (text !== before) {
    fs.writeFileSync(file, text, 'utf8')
    console.log('fixed', file)
  } else {
    console.log('ok', file)
  }
}
