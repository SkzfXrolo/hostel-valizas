import fs from 'fs'

let s = fs.readFileSync('src/i18n.js', 'utf8')
s = s.replace(/^export /gm, '')
s = s.replace(/localStorage/g, '({getItem:()=>null,setItem:()=>{}})')
s = s.replace(/\bdocument\b/g, '({documentElement:{},querySelectorAll:()=>[]})')
s = s.replace(/\bwindow\b/g, '({dispatchEvent:()=>{}})')

const { dict } = new Function(s + '; return { dict };')()

const sample = ['home.ico.pool', 'home.loc.title', 'home.stat.pool', 'ideal.camps', 'exp.g.pool']
for (const lang of ['es', 'en', 'pt']) {
  console.log(lang, Object.fromEntries(sample.map((k) => [k, dict[lang][k]])))
}
console.log('top-level orphan home.ico.pool?', Object.hasOwn(dict, 'home.ico.pool'))

const html = fs.readFileSync('index.html', 'utf8')
const used = [...html.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1])
const missing = [...new Set(used)].filter((k) => !dict.es[k])
console.log('missing in es:', missing.length ? missing.join(', ') : 'none')
