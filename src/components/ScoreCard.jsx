import { createPortal } from 'react-dom'
import { useEffect } from 'react'
import './ScoreCard.css'

function fmtMoney(v) {
  if (v == null || !isFinite(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function roiColor(roi) {
  if (roi >= 200) return '#fbc02d'
  if (roi >= 60)  return '#4caf50'
  return 'rgba(224,232,255,0.6)'
}

const GRADE_COLORS = {
  F: '#d32f2f', E: '#f57c00', D: '#fbc02d',
  C: '#8bc34a', B: '#43a047', A: '#2e7d32',
}
const GRADE_LABELS = {
  F: 'Critical',  E: 'Severe',    D: 'Poor',
  C: 'Moderate',  B: 'Fair',      A: 'Good',
}

function gradeColor(grade) {
  return GRADE_COLORS[grade?.charAt(0)] ?? '#9e9e9e'
}

function ScoreBar({ label, value, color }) {
  return (
    <div className="sc-bar-row">
      <span className="sc-bar-label">{label}</span>
      <div className="sc-bar-track">
        <div
          className="sc-bar-fill"
          style={{ width: `${Math.min(100, value)}%`, background: color }}
        />
      </div>
      <span className="sc-bar-val">{value.toFixed(0)}</span>
    </div>
  )
}

function HeatmapThumb({ src, alt }) {
  return (
    <a href={src} target="_blank" rel="noopener noreferrer" className="sc-thumb-link">
      <img src={src} alt={alt} className="sc-thumb" />
      <span className="sc-thumb-label">{alt}</span>
    </a>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export default function ScoreCard({ item, finance = null, onClose }) {
  // Close on Escape
  useEffect(() => {
    const fn = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])

  if (!item) return null

  const isSite = item._type === 'site'

  // Normalise fields between main-site and batch-courtyard shapes
  const name         = isSite ? item.name        : `${(item.site_name ?? item.site_key).split('—')[0].trim()} — ${item.patch_label}`
  const score        = isSite ? item.composite_score : item.composite
  const grade        = item.grade_short ?? item.grade?.charAt(0) ?? '?'
  const gradeLabel   = GRADE_LABELS[grade] ?? grade
  const color        = gradeColor(grade)
  const components   = isSite ? (item.components ?? {}) : {
    [item.wind_stat_label  ?? 'Wind']:  item.wind_score  ?? 0,
    [item.solar_stat_label ?? 'Solar']: item.solar_score ?? 0,
    [item.utci_stat_label  ?? 'UTCI']:  item.utci_score  ?? 0,
  }
  const keyStats     = isSite ? (item.key_stats ?? {}) : null
  const best         = isSite ? item.best_intervention : null
  const scenarios    = isSite ? (item.all_scenarios ?? {}) : {}
  const heatmaps     = isSite ? (item.heatmaps ?? {}) : {}

  // Pick 3 key heatmap thumbnails for main sites
  const thumbKeys = ['baseline_utci', 'baseline_wind', 'baseline_sun']
  const thumbs = thumbKeys
    .filter(k => heatmaps[k])
    .map(k => ({ key: k, src: `/${heatmaps[k]}`, alt: k.replace('baseline_', '') }))

  const card = (
    <div className="sc-overlay">
      <div className="sc-card">
        {/* Close button */}
        <button className="sc-close" onClick={onClose} aria-label="Close">&#x2715;</button>

        {/* Grade badge + title */}
        <div className="sc-header">
          <div
            className="sc-grade-badge"
            style={{ background: color }}
          >
            <span className="sc-grade-letter">{grade}</span>
            <span className="sc-grade-label">{gradeLabel}</span>
          </div>
          <div className="sc-title-block">
            <div className="sc-name">{name}</div>
            <div className="sc-score-row">
              <div className="sc-score-track">
                <div
                  className="sc-score-fill"
                  style={{ width: `${score}%`, background: color }}
                />
              </div>
              <span className="sc-score-num" style={{ color }}>{score.toFixed(1)}</span>
              <span className="sc-score-unit">&nbsp;/&nbsp;100</span>
            </div>
          </div>
        </div>

        {/* Component breakdown */}
        <div className="sc-section">
          <div className="sc-section-label">COMPONENT SCORES</div>
          {Object.entries(components).map(([label, val]) => (
            <ScoreBar key={label} label={label} value={val} color={color} />
          ))}
        </div>

        {/* Measurements (batch courtyards only) */}
        {!isSite && (
          <div className="sc-section">
            <div className="sc-section-label">MEASUREMENTS</div>
            <div className="sc-stats-grid">
              <div className="sc-stat">
                <span className="sc-stat-val">{item.wind_val?.toFixed(2) ?? '—'}</span>
                <span className="sc-stat-unit">m/s wind</span>
              </div>
              <div className="sc-stat">
                <span className="sc-stat-val">{item.solar_val != null ? (item.solar_val * 100).toFixed(1) : '—'}</span>
                <span className="sc-stat-unit">% direct sun</span>
              </div>
              <div className="sc-stat">
                <span className="sc-stat-val">#{item.rank ?? '—'}</span>
                <span className="sc-stat-unit">site rank</span>
              </div>
            </div>
          </div>
        )}

        {/* Key stats (main sites only) */}
        {keyStats && (
          <div className="sc-section">
            <div className="sc-section-label">KEY STATS</div>
            <div className="sc-stats-grid">
              <div className="sc-stat">
                <span className="sc-stat-val">{keyStats.wind_mean_ms}</span>
                <span className="sc-stat-unit">m/s wind</span>
              </div>
              <div className="sc-stat">
                <span className="sc-stat-val">{keyStats.sun_mean_h_day}</span>
                <span className="sc-stat-unit">h/day sun</span>
              </div>
              <div className="sc-stat">
                <span className="sc-stat-val">{keyStats.utci_mean_c}</span>
                <span className="sc-stat-unit">&#xb0;C UTCI</span>
              </div>
            </div>
          </div>
        )}

        {/* Interventions (main sites only) */}
        {Object.keys(scenarios).length > 0 && (
          <div className="sc-section">
            <div className="sc-section-label">INTERVENTIONS</div>
            {Object.entries(scenarios).map(([k, s]) => (
              <div
                key={k}
                className={`sc-scenario${best?.key === k ? ' sc-scenario--best' : ''}`}
              >
                <span className="sc-scenario-key">[{k}]</span>
                <div className="sc-scenario-body">
                  <div className="sc-scenario-label">{s.label}</div>
                  <div className="sc-scenario-delta">
                    <span style={{ color: s.wind_improv_ms >= 0 ? '#4caf50' : '#f44336' }}>
                      wind {s.wind_improv_ms >= 0 ? '+' : ''}{s.wind_improv_ms?.toFixed(3)} m/s
                    </span>
                    <span className="sc-dot">&#x2022;</span>
                    <span style={{ color: s.utci_improv_c >= 0 ? '#4caf50' : '#f44336' }}>
                      UTCI {s.utci_improv_c >= 0 ? '+' : ''}{s.utci_improv_c?.toFixed(2)}&deg;C
                    </span>
                    <span className="sc-dot">&#x2022;</span>
                    <span className="sc-scenario-frac">{s.frac_utci_pct?.toFixed(0)}% cells improved</span>
                  </div>
                </div>
                {best?.key === k && finance && (
                  <div className="sc-scenario-finance">
                    <span
                      className="sc-fin-roi"
                      style={{ color: roiColor(finance.roi_pct) }}
                    >
                      {finance.roi_pct.toFixed(0)}% ROI
                    </span>
                    <span className="sc-dot">&#x2022;</span>
                    <span className="sc-fin-val">NPV {fmtMoney(finance.npv_usd)}</span>
                    <span className="sc-dot">&#x2022;</span>
                    <span className="sc-fin-val">Capex {fmtMoney(finance.capex_usd)}</span>
                    {finance.stranded_rcp45 && (
                      <span className="sc-fin-stranded" title="Stranded asset: projected outdoor thermal conditions (UTCI) exceed 46 °C by 2050 under RCP 4.5 warming. Outdoor spaces become economically unviable — property values face a mandatory discount (up to 25%). Renovation scenarios reduce current UTCI but cannot fully offset the 2050 trajectory.">&#x26a0; Stranded 2050</span>
                    )}
                  </div>
                )}
                {best?.key === k && <span className="sc-best-tag">BEST</span>}
              </div>
            ))}
          </div>
        )}

        {/* Heatmap thumbnails */}
        {thumbs.length > 0 && (
          <div className="sc-section">
            <div className="sc-section-label">HEATMAPS (click to enlarge)</div>
            <div className="sc-thumbs">
              {thumbs.map(t => (
                <HeatmapThumb key={t.key} src={t.src} alt={t.alt} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )

  // Portal: render directly under <body> so Leaflet stacking contexts
  // can never put the overlay behind the map tiles.
  return createPortal(card, document.body)
}
