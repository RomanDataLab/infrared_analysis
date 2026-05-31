import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import ScoreCard from './ScoreCard'
import './CityMap.css'

// ── Compute study-area bounds from site centre — size in metres (500 or 1000) ──
function siteBounds(lat, lon, size = 500) {
  const half    = size / 2
  const halfLat = half / 111320
  const halfLon = half / (111320 * Math.cos(lat * Math.PI / 180))
  return [
    [lat - halfLat, lon - halfLon],  // SW
    [lat + halfLat, lon + halfLon],  // NE
  ]
}

// ── Actual API grid bounds — use these for the heatmap overlay ───────────────
// site.overlay_bounds = [W, S, E, N] = [min_lng, min_lat, max_lng, max_lat]
// saved from AreaResult.bounds after each baseline run.
// Falls back to siteBounds() when not yet available (pending sites).
function heatmapBounds(site) {
  if (site?.overlay_bounds) {
    const [w, s, e, n] = site.overlay_bounds
    return [[s, w], [n, e]]   // Leaflet: [[SW_lat, SW_lon], [NE_lat, NE_lon]]
  }
  return siteBounds(site.lat, site.lon)
}

const GRADE_COLORS = {
  F: '#d32f2f', E: '#f57c00', D: '#fbc02d',
  C: '#8bc34a', B: '#43a047', A: '#2e7d32',
}

const LAYER_LABELS = {
  baseline_utci:  'UTCI',
  baseline_wind:  'Wind',
  baseline_sun:   'Sun',
}

const LAYER_KEYS = ['baseline_utci', 'baseline_wind', 'baseline_sun']

// ── Per-layer legend config ───────────────────────────────────────────────────
const LAYER_LEGENDS = {
  baseline_utci: {
    title: 'UTCI — thermal comfort',
    gradient: 'linear-gradient(to right, #1a237e, #1565c0, #4caf50, #fbc02d, #e53935)',
    lo: 'Cold stress',
    hi: 'Heat stress',
  },
  baseline_wind: {
    title: 'Wind speed',
    gradient: 'linear-gradient(to right, #0d47a1, #1976d2, #43a047, #fbc02d, #b71c1c)',
    lo: 'Calm',
    hi: 'Strong',
  },
  baseline_sun: {
    title: 'Solar exposure',
    gradient: 'linear-gradient(to right, #1a1a2e, #1a237e, #f57f17, #fff176)',
    lo: 'No sun',
    hi: 'Full sun',
  },
}

function gradeColor(g) { return GRADE_COLORS[g] ?? '#9e9e9e' }

// ── Finance helpers ───────────────────────────────────────────────────────────
function fmtMoney(v) {
  if (v == null || !isFinite(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function roiColor(roi) {
  if (roi >= 200) return '#fbc02d'             // gold — exceptional
  if (roi >= 60)  return '#4caf50'             // green — solid
  return 'rgba(224,232,255,0.55)'              // neutral
}

// ── Component ────────────────────────────────────────────────────────────────
function IconMaximize() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 3 21 3 21 9" />
      <polyline points="9 21 3 21 3 15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  )
}

function IconMinimize() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 14 10 14 10 20" />
      <polyline points="20 10 14 10 14 4" />
      <line x1="10" y1="14" x2="3" y2="21" />
      <line x1="21" y1="3" x2="14" y2="10" />
    </svg>
  )
}

export default function CityMap({ site, batch = [], locked = false, finance = null, maximized = false, onToggleMaximize, studySize = 500 }) {
  const containerRef = useRef(null)
  const mapRef       = useRef(null)
  const overlayRef   = useRef(null)
  const rectRef      = useRef(null)
  const markersRef   = useRef([])
  const [activeLayer,    setActiveLayer]    = useState('baseline_utci')
  const [overlayOn,      setOverlayOn]      = useState(true)
  const [showCard,       setShowCard]       = useState(false)
  const [mapInitialized, setMapInitialized] = useState(false)
  const [selectedBatch,  setSelectedBatch]  = useState(null)

  // ── Init Leaflet once ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!site || mapRef.current) return

    const rectBounds = siteBounds(site.lat, site.lon, studySize)   // study-area border
    const imgBounds  = heatmapBounds(site)                         // actual API grid extent

    const map = L.map(containerRef.current, {
      zoomControl:        true,
      attributionControl: false,
    })

    // Satellite base layer — Mapbox Satellite (best OSM alignment globally)
    const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN ?? ''
    L.tileLayer(
      `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{z}/{x}/{y}?access_token=${MAPBOX_TOKEN}`,
      { maxZoom: 20, tileSize: 512, zoomOffset: -1 }
    ).addTo(map)

    // Streets label overlay (subtle)
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
      { maxZoom: 19, opacity: 0.55 }
    ).addTo(map)

    // Study area boundary — track in rectRef so studySize changes can update it
    rectRef.current = L.rectangle(rectBounds, {
      color:     '#fbc02d',
      weight:    2.5,
      fill:      false,
      dashArray: '8,5',
    }).addTo(map)

    // Metric scale bar — bottom-right, metric only
    L.control.scale({ imperial: false, position: 'bottomright' }).addTo(map)

    // Heatmap overlay — stretched over the ACTUAL API grid bounds so pixels
    // land on the correct geographic coordinates regardless of tile-snap.
    const overlay = L.imageOverlay(
      `/${site.heatmaps?.baseline_utci_overlay ?? `heatmaps/${site.key}/baseline_utci_overlay.png`}`,
      imgBounds,
      { opacity: 0.72 }
    ).addTo(map)
    overlayRef.current = overlay

    // Fit after a short delay so the CSS layout has settled and Leaflet
    // reads the correct container dimensions — avoids wrong initial zoom.
    setTimeout(() => {
      map.invalidateSize({ animate: false })
      map.fitBounds(rectBounds, { padding: [40, 40], animate: false })
      setMapInitialized(true)
    }, 60)
    mapRef.current = map

    // ResizeObserver keeps Leaflet informed whenever the CSS grid resizes
    // the pane (e.g. window resize, sidebar toggle).  Without this, cached
    // stale dimensions produce wrong zoom levels on fitBounds calls.
    const ro = new ResizeObserver(() => {
      if (mapRef.current) mapRef.current.invalidateSize({ animate: false })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      markersRef.current.forEach(m => { try { m.remove() } catch (_) {} })
      markersRef.current = []
      map.remove()
      mapRef.current     = null
      overlayRef.current = null
    }
  }, [site])

// ── Lock / unlock all map interactions ───────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const handlers = [
      'dragging', 'touchZoom', 'doubleClickZoom',
      'scrollWheelZoom', 'boxZoom', 'keyboard',
    ]
    handlers.forEach(h => { if (map[h]) map[h][locked ? 'disable' : 'enable']() })
    if (map.tap) map.tap[locked ? 'disable' : 'enable']()
  }, [locked])

  // ── Batch courtyard markers ───────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!mapInitialized || !map || !batch.length) return

    // Remove any previous markers
    markersRef.current.forEach(m => { try { map.removeLayer(m) } catch (_) {} })
    markersRef.current = []

    batch.forEach(b => {
      const color = GRADE_COLORS[b.grade_short] ?? '#9e9e9e'
      const icon  = L.divIcon({
        className: '',
        html: `<div class="courtyard-marker" style="background:${color}">${b.grade_short}</div>`,
        iconSize:   [20, 20],
        iconAnchor: [10, 10],
      })
      const marker = L.marker([b.lat, b.lon], {
          icon,
          title: `${b.patch_label} — Grade ${b.grade_short} (${b.composite.toFixed(0)}/100)`,
        })
        .on('click', () => {
          setShowCard(false)
          setSelectedBatch(prev => (prev?.patch_id === b.patch_id ? null : b))
        })
        .addTo(map)
      markersRef.current.push(marker)
    })
  }, [mapInitialized, batch])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Swap heatmap layer on tab change (crossfade) ─────────────────────────
  useEffect(() => {
    const map        = mapRef.current
    const oldOverlay = overlayRef.current
    if (!map || !oldOverlay || !site) return

    const imgBounds   = heatmapBounds(site)
    const targetOpacity = overlayOn ? 0.72 : 0

    // New overlay starts transparent — CSS transition fades it in
    const next = L.imageOverlay(
      `/${site.heatmaps?.[`${activeLayer}_overlay`] ?? `heatmaps/${site.key}/${activeLayer}_overlay.png`}`,
      imgBounds,
      { opacity: 0 }
    ).addTo(map)
    overlayRef.current = next

    // Trigger CSS transition in the next paint frame
    requestAnimationFrame(() => { next.setOpacity(targetOpacity) })

    // Remove old overlay after the 200 ms fade completes
    const timer = setTimeout(() => {
      try { oldOverlay.remove() } catch (_) {}
    }, 220)

    return () => clearTimeout(timer)
  }, [activeLayer, site])

  // ── Toggle overlay on/off (fade without swapping the image) ──────────────
  useEffect(() => {
    const overlay = overlayRef.current
    if (!overlay) return
    overlay.setOpacity(overlayOn ? 0.72 : 0)
  }, [overlayOn])

  // ── Update rectangle + re-fit when study size changes ───────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !site) return
    const newBounds = siteBounds(site.lat, site.lon, studySize)
    if (rectRef.current) { rectRef.current.remove() }
    rectRef.current = L.rectangle(newBounds, {
      color: '#fbc02d', weight: 2.5, fill: false, dashArray: '8,5',
    }).addTo(map)
    map.invalidateSize({ animate: false })
    map.fitBounds(newBounds, { padding: [40, 40], animate: false })
  }, [studySize])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Re-fit study area when pane is maximised / restored ──────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !site) return
    const timer = setTimeout(() => {
      map.invalidateSize({ animate: false })
      map.fitBounds(siteBounds(site.lat, site.lon, studySize), { padding: [40, 40], animate: false })
    }, 80)
    return () => clearTimeout(timer)
  }, [maximized])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── 1 / 2 / 3 keyboard shortcuts to cycle heatmap layers ──────────────────
  useEffect(() => {
    const fn = e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === '1') { setActiveLayer('baseline_utci'); setOverlayOn(true) }
      if (e.key === '2') { setActiveLayer('baseline_wind'); setOverlayOn(true) }
      if (e.key === '3') { setActiveLayer('baseline_sun');  setOverlayOn(true) }
    }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [])

  if (!site) return null

  const color = gradeColor(site.grade_short)
  const ks    = site.key_stats ?? {}

  // Legend bottom offset — clears city-footer (~32px) and city-finance (~27px)
  // when those strips are visible, so the legend never overlaps them.
  const legendBottom = 10 + (site.best_intervention ? 32 : 0) + (finance ? 27 : 0)

  return (
    <div className="city-map">

      {/* ── Top bar — entire bar is clickable ── */}
      <div
        className="city-bar"
        style={{ borderLeftColor: color, cursor: 'pointer' }}
        onClick={() => { setSelectedBatch(null); setShowCard(s => !s) }}
        title="Show full score card"
      >
        <div
          className="city-grade"
          style={{ background: color }}
        >
          {site.grade_short}
        </div>

        <div className="city-meta">
          <span className="city-name">{site.name}</span>
          <span className="city-score" style={{ color }}>
            {site.composite_score.toFixed(0)}&nbsp;<span className="city-score-denom">/&nbsp;100</span>
          </span>
        </div>

        {/* Key stats — placed before layer buttons so margin-left:auto on layers
            pushes layers+maximize to the right rather than wrapping stats down */}
        <div className="city-stats">
          <span>{ks.wind_mean_ms ?? '—'} m/s</span>
          <span className="stat-dot">·</span>
          <span>{ks.sun_mean_h_day ?? '—'} h/day</span>
          <span className="stat-dot">·</span>
          <span>{ks.utci_mean_c ?? '—'}°C UTCI</span>
        </div>

        {/* Layer selector — stop propagation so bar click doesn't also toggle card */}
        <div className="city-layers" onClick={e => e.stopPropagation()}>
          {LAYER_KEYS.map((key, i) => {
            const isActive  = activeLayer === key
            const isHidden  = isActive && !overlayOn
            return (
              <button
                key={key}
                className={`layer-btn${isActive ? ' active' : ''}${isHidden ? ' layer-btn-off' : ''}`}
                style={isActive && overlayOn ? { borderColor: color, color } : {}}
                onClick={() => {
                  if (isActive) {
                    setOverlayOn(v => !v)   // re-click active → toggle visibility
                  } else {
                    setActiveLayer(key)
                    setOverlayOn(true)       // switching layer always shows it
                  }
                }}
                title={isActive
                  ? (overlayOn ? `Hide overlay (click again to show)` : `Show overlay`)
                  : `${LAYER_LEGENDS[key].title} (shortcut: ${i + 1})`
                }
              >
                {LAYER_LABELS[key]}
              </button>
            )
          })}
        </div>

        {/* Maximize / restore button */}
        {onToggleMaximize && (
          <button
            className={`city-maximize-btn${maximized ? ' active' : ''}`}
            onClick={e => { e.stopPropagation(); onToggleMaximize() }}
            title={maximized ? 'Restore grid view' : 'Maximise this map'}
          >
            {maximized ? <IconMinimize /> : <IconMaximize />}
          </button>
        )}
      </div>

      {/* ── Leaflet map ── */}
      <div ref={containerRef} className="city-canvas" />

      {/* ── Bottom strip: best intervention ── */}
      {site.best_intervention && (
        <div className="city-footer">
          <span className="footer-prefix">Best intervention</span>
          <span className="footer-label">[{site.best_intervention.key}] {site.best_intervention.label}</span>
          <span
            className="footer-gain"
            style={{ color: site.best_intervention.utci_improv_c >= 0 ? '#4caf50' : '#f44336' }}
          >
            UTCI {site.best_intervention.utci_improv_c >= 0 ? '+' : ''}
            {site.best_intervention.utci_improv_c?.toFixed(2)}°C
          </span>
        </div>
      )}

      {/* ── Heatmap legend — hidden when overlay is toggled off ── */}
      <div
        className="map-legend"
        style={{ bottom: legendBottom, opacity: overlayOn ? 1 : 0, transition: 'opacity 0.2s ease' }}
        aria-hidden="true"
      >
        <div className="map-legend-title">{LAYER_LEGENDS[activeLayer]?.title}</div>
        <div
          className="map-legend-bar"
          style={{ background: LAYER_LEGENDS[activeLayer]?.gradient }}
        />
        <div className="map-legend-ticks">
          <span>{LAYER_LEGENDS[activeLayer]?.lo}</span>
          <span>{LAYER_LEGENDS[activeLayer]?.hi}</span>
        </div>
      </div>

      {/* ── ScoreCard overlay — site ── */}
      {showCard && (
        <ScoreCard
          item={{ ...site, _type: 'site' }}
          finance={finance}
          onClose={() => setShowCard(false)}
        />
      )}

      {/* ── ScoreCard overlay — courtyard ── */}
      {selectedBatch && (
        <ScoreCard
          item={{ ...selectedBatch, _type: 'batch' }}
          onClose={() => setSelectedBatch(null)}
        />
      )}

      {/* ── Finance strip ── */}
      {finance && (
        <div className="city-finance">
          <span className="finance-prefix">NPV</span>
          <span className="finance-npv">{fmtMoney(finance.npv_usd)}</span>
          <span className="stat-dot">·</span>
          <span className="finance-roi" style={{ color: roiColor(finance.roi_pct) }}>
            {finance.roi_pct.toFixed(0)}% ROI
          </span>
          <span className="stat-dot">·</span>
          <span className="finance-scenario">
            Scenario {finance.scenario_key}
          </span>
          {finance.stranded_rcp45 && (
            <span className="finance-stranded" title="Projected UTCI ≥ 46 °C by 2050 under RCP 4.5">
              ⚠ Stranded 2050
            </span>
          )}
        </div>
      )}
    </div>
  )
}
