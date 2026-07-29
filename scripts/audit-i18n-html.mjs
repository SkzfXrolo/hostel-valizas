import fs from 'fs'
import path from 'path'

const root = process.cwd()
let s = fs.readFileSync('src/i18n.js', 'utf8')
s = s.replace(/^export /gm, '')
s = s.replace(/localStorage/g, '({getItem:()=>null,setItem:()=>{}})')
s = s.replace(/\bdocument\b/g, '({documentElement:{},querySelectorAll:()=>[]})')
s = s.replace(/\bwindow\b/g, '({dispatchEvent:()=>{}})')
const { dict } = new Function(s + '; return { dict };')()

const htmlFiles = fs
  .readdirSync(root)
  .filter((f) => f.endsWith('.html'))

const missing = []
for (const file of htmlFiles) {
  const html = fs.readFileSync(file, 'utf8')
  const keys = [...html.matchAll(/data-i18n(?:-html|-placeholder|-aria|-title)?="([^"]+)"/g)].map(
    (m) => m[1],
  )
  for (const key of new Set(keys)) {
    if (!dict.es[key]) missing.push(`${file}: ${key}`)
  }
}
console.log(missing.length ? missing.join('\n') : 'all html data-i18n keys present in es')
