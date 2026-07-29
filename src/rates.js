import { getContentSync, DEFAULTS } from './contentStore.js'

/** @deprecated use getContentSync — kept for imports */
export const RATE_TABLE = { months: DEFAULTS.rateMonths }
export const BLOCKED_DATES = DEFAULTS.blockedDates
export let USD_TO_UYU = DEFAULTS.usdToUyu

export function isBlocked(iso) {
  const { blockedDates } = getContentSync()
  return blockedDates.includes(iso)
}

export function ratesForMonth(month) {
  const { rateMonths } = getContentSync()
  return rateMonths[month] || rateMonths[5]
}

export function getUsdToUyu() {
  return getContentSync().usdToUyu || DEFAULTS.usdToUyu
}

export function renderRatesTable(container, t) {
  if (!container) return
  const { rateMonths, usdToUyu } = getContentSync()
  const lang = document.documentElement.lang
  const locale = lang === 'en' ? 'en-US' : lang === 'pt' ? 'pt-BR' : 'es-UY'
  const monthNames = Array.from({ length: 12 }, (_, i) =>
    new Date(2024, i, 1).toLocaleDateString(locale, { month: 'short' }),
  )

  const rows = Object.entries(rateMonths)
    .map(([m, r]) => {
      const mi = Number(m) - 1
      return `<tr data-season="${r.season}">
        <td>${monthNames[mi]}</td>
        <td>$${r.suite[0]}–${r.suite[1]}</td>
        <td>$${r.doble[0]}–${r.doble[1]}</td>
        <td>$${r.dorm[0]}–${r.dorm[1]}</td>
        <td><span class="season-pill season-pill--${r.season}">${t(`pricing.legend.${r.season}`)}</span></td>
      </tr>`
    })
    .join('')

  container.innerHTML = `
    <div class="rates-table-wrap">
      <table class="rates-table">
        <thead>
          <tr>
            <th>${t('rates.month')}</th>
            <th>${t('rates.suite')}</th>
            <th>${t('rates.doble')}</th>
            <th>${t('rates.dorm')}</th>
            <th>${t('rates.season')}</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="rates-disclaimer">${t('rates.disclaimer', { uyu: usdToUyu })}</p>
    </div>
  `
}
