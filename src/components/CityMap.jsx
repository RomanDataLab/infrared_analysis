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
// Supports per-site overlay_offset [dLon, dLat] for manual alignment correction.
function heatmapBounds(site) {
  if (site?.overlay_bounds) {
    const [w, s, e, n] = site.overlay_bounds
    const [dLon, dLat] = site.overlay_offset ?? [0, 0]
    return [[s + dLat, w + dLon], [n + dLat, e + dLon]]
  }
  return siteBounds(site.lat, site.lon)
}

// ── Fetch simulation building footprints ─────────────────────────────────────
// Priority: pre-generated GeoJSON (exact sim buildings, OSM+Overture color-coded)
// Fallback: live Overpass API (OSM only)
const _buildingCache = {}

async function fetchSimBuildings(siteKey, size) {
  const cacheKey = `${siteKey}_${size}`
  if (_buildingCache[cacheKey]) return _buildingCache[cacheKey]

  const subdir = size === 1000 ? '/1km' : ''
  const url = `/heatmaps/${siteKey}${subdir}/buildings.geojson`

  try {
    const resp = await fetch(url)
    if (resp.ok) {
      const geojson = await resp.json()
      _buildingCache[cacheKey] = geojson
      return geojson
    }
  } catch (_) { /* fall through to Overpass */ }

  // Fallback: live Overpass API (browser-side, may fail behind firewalls)
  return fetchOverpassBuildings(siteKey, size)
}

async function fetchOverpassBuildings(siteKey, size) {
  const cacheKey = `overpass_${siteKey}_${size}`
  if (_buildingCache[cacheKey]) return _buildingCache[cacheKey]

  const rdFile = size === 1000 ? '/renovation_data_1km.json' : '/renovation_data.json'
  const resp1 = await fetch(rdFile)
  const rd = await resp1.json()
  const site = (rd.sites ?? []).find(s => s.key === siteKey)
  if (!site) return { type: 'FeatureCollection', features: [] }

  const { lat, lon } = site
  const half    = (size / 2 + 50)
  const halfLat = half / 111320
  const halfLon = half / (111320 * Math.cos(lat * Math.PI / 180))
  const bbox = `${lat - halfLat},${lon - halfLon},${lat + halfLat},${lon + halfLon}`

  const query = `[out:json][timeout:15];(way["building"](${bbox});relation["building"](${bbox}););out geom;`
  const resp = await fetch(
    `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`
  )
  const data = await resp.json()

  const features = []
  for (const el of data.elements ?? []) {
    if (el.type === 'way' && el.geometry) {
      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [el.geometry.map(p => [p.lon, p.lat])] },
        properties: { source: 'osm', height: el.tags?.height ?? null, name: el.tags?.name ?? '' },
      })
    } else if (el.type === 'relation' && el.members) {
      for (const m of el.members) {
        if (m.type === 'way' && m.role === 'outer' && m.geometry) {
          features.push({
            type: 'Feature',
            geometry: { type: 'Polygon', coordinates: [m.geometry.map(p => [p.lon, p.lat])] },
            properties: { source: 'osm', name: el.tags?.name ?? '' },
          })
        }
      }
    }
  }

  const geojson = { type: 'FeatureCollection', features }
  _buildingCache[cacheKey] = geojson
  return geojson
}

// ── Building style: OSM = cyan, Overture = magenta ──────────────────────────
const BLDG_STYLES = {
  osm:      { color: '#00e5ff', fillColor: '#00e5ff', weight: 1.5, fillOpacity: 0.08, opacity: 0.85 },
  overture: { color: '#e040fb', fillColor: '#e040fb', weight: 1.5, fillOpacity: 0.10, opacity: 0.85 },
  ms:       { color: '#76ff03', fillColor: '#76ff03', weight: 1.5, fillOpacity: 0.10, opacity: 0.85 },
}

function bldgStyle(feature) {
  return BLDG_STYLES[feature.properties?.source] ?? BLDG_STYLES.osm
}

// ── Fetch tree canopy GeoJSON ────────────────────────────────────────────────
const _treeCache = {}

async function fetchTrees(siteKey, size) {
  const cacheKey = `${siteKey}_${size}`
  if (_treeCache[cacheKey]) return _treeCache[cacheKey]

  const subdir = size === 1000 ? '/1km' : ''
  const url = `/heatmaps/${siteKey}${subdir}/trees.geojson`

  try {
    const resp = await fetch(url)
    if (resp.ok) {
      const geojson = await resp.json()
      _treeCache[cacheKey] = geojson
      return geojson
    }
  } catch (_) { /* no trees available */ }

  return { type: 'FeatureCollection', features: [] }
}

// ── Tree canopy styles ──────────────────────────────────────────────────────
const TREE_STYLES = {
  osm:    { color: '#66bb6a', fillColor: '#66bb6a', weight: 1.2, fillOpacity: 0.18, opacity: 0.80 },
  ground: { color: '#2e7d32', fillColor: '#2e7d32', weight: 1.0, fillOpacity: 0.12, opacity: 0.65 },
}

function treeStyle(feature) {
  return TREE_STYLES[feature.properties?.source] ?? TREE_STYLES.osm
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
    title: 'UTCI \u2014 thermal comfort',
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
  if (v == null || !isFinite(v)) return '\u2014'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function roiColor(roi) {
  if (roi >= 200) return '#fbc02d'
  if (roi >= 60)  return '#4caf50'
  return 'rgba(224,232,255,0.55)'
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
  const containerRef    = useRef(null)
  const mapRef          = useRef(null)
  const overlayRef      = useRef(null)
  const rectRef         = useRef(null)
  const markersRef      = useRef([])
  const buildingsRef    = useRef(null)
  const treesRef        = useRef(null)
  const [activeLayer,    setActiveLayer]    = useState('baseline_utci')
  const [overlayOn,      setOverlayOn]      = useState(true)
  const [showCard,       setShowCard]       = useState(false)
  const [mapInitialized, setMapInitialized] = useState(false)
  const [selectedBatch,  setSelectedBatch]  = useState(null)
  const [showBuildings,  setShowBuildings]  = useState(false)
  const [bldgLoading,    setBldgLoading]    = useState(false)
  const [bldgCount,      setBldgCount]      = useState(null)
  const [showTrees,      setShowTrees]      = useState(false)
  const [treeLoading,    setTreeLoading]    = useState(false)
  const [treeCount,      setTreeCount]      = useState(null)

  // ── Init Leaflet once ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!site || mapRef.current) return

    const rectBounds = siteBounds(site.lat, site.lon, studySize)
    const imgBounds  = heatmapBounds(site)

    const map = L.map(containerRef.current, {
      zoomControl:        true,
      attributionControl: false,
    })

    const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN ?? ''
    L.tileLayer(
      `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{z}/{x}/{y}?access_token=${MAPBOX_TOKEN}`,
      { maxZoom: 20, tileSize: 512, zoomOffset: -1 }
    ).addTo(map)

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
      { maxZoom: 19, opacity: 0.55 }
    ).addTo(map)

    rectRef.current = L.rectangle(rectBounds, {
      color: '#fbc02d', weight: 2.5, fill: false, dashArray: '8,5',
    }).addTo(map)

    L.control.scale({ imperial: false, position: 'bottomright' }).addTo(map)

    const overlay = L.imageOverlay(
      `/${site.heatmaps?.baseline_utci_overlay ?? `heatmaps/${site.key}/baseline_utci_overlay.png`}`,
      imgBounds,
      { opacity: 0.72 }
    ).addTo(map)
    overlayRef.current = overlay

    setTimeout(() => {
      map.invalidateSize({ animate: false })
      map.fitBounds(rectBounds, { padding: [40, 40], animate: false })
      setMapInitialized(true)
    }, 60)
    mapRef.current = map

    const ro = new ResizeObserver(() => {
      if (mapRef.current) mapRef.current.invalidateSize({ animate: false })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      markersRef.current.forEach(m => { try { m.remove() } catch (_e) {} })
      markersRef.current = []
      if (buildingsRef.current) { try { buildingsRef.current.remove() } catch (_e) {} }
      buildingsRef.current = null
      if (treesRef.current) { try { treesRef.current.remove() } catch (_e) {} }
      treesRef.current = null
      map.remove()
      mapRef.current     = null
      overlayRef.current = null
    }
  }, [site])

  // ── Lock / unlock ─────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const handlers = ['dragging', 'touchZoom', 'doubleClickZoom', 'scrollWheelZoom', 'boxZoom', 'keyboard']
    handlers.forEach(h => { if (map[h]) map[h][locked ? 'disable' : 'enable']() })
    if (map.tap) map.tap[locked ? 'disable' : 'enable']()
  }, [locked])

  // ── Batch courtyard markers ───────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!mapInitialized || !map || !batch.length) return
    markersRef.current.forEach(m => { try { map.removeLayer(m) } catch (_) {} })
    markersRef.current = []
    batch.forEach(b => {
      const color = GRADE_COLORS[b.grade_short] ?? '#9e9e9e'
      const icon  = L.divIcon({
        className: '',
        html: `<div class="courtyard-marker" style="background:${color}">${b.grade_short}</div>`,
        iconSize: [20, 20], iconAnchor: [10, 10],
      })
      const marker = L.marker([b.lat, b.lon], {
          icon, title: `${b.patch_label} \u2014 Grade ${b.grade_short} (${b.composite.toFixed(0)}/100)`,
        })
        .on('click', () => { setShowCard(false); setSelectedBatch(prev => (prev?.patch_id === b.patch_id ? null : b)) })
        .addTo(map)
      markersRef.current.push(marker)
    })
  }, [mapInitialized, batch])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Swap heatmap layer on tab change (crossfade) ─────────────────────────
  useEffect(() => {
    const map = mapRef.current, oldOverlay = overlayRef.current
    if (!map || !oldOverlay || !site) return
    const imgBounds = heatmapBounds(site)
    const targetOpacity = overlayOn ? 0.72 : 0
    const next = L.imageOverlay(
      `/${site.heatmaps?.[`${activeLayer}_overlay`] ?? `heatmaps/${site.key}/${activeLayer}_overlay.png`}`,
      imgBounds, { opacity: 0 }
    ).addTo(map)
    overlayRef.current = next
    requestAnimationFrame(() => { next.setOpacity(targetOpacity) })
    const timer = setTimeout(() => { try { oldOverlay.remove() } catch (_) {} }, 220)
    return () => clearTimeout(timer)
  }, [activeLayer, site])

  // ── Toggle overlay visibility ─────────────────────────────────────────────
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

  // ── Re-fit on maximize / restore ──────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !site) return
    const timer = setTimeout(() => {
      map.invalidateSize({ animate: false })
      map.fitBounds(siteBounds(site.lat, site.lon, studySize), { padding: [40, 40], animate: false })
    }, 80)
    return () => clearTimeout(timer)
  }, [maximized])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Keyboard shortcuts: 1-3 layers, 4 buildings ──────────────────────────
  useEffect(() => {
    const fn = e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === '1') { setActiveLayer('baseline_utci'); setOverlayOn(true) }
      if (e.key === '2') { setActiveLayer('baseline_wind'); setOverlayOn(true) }
      if (e.key === '3') { setActiveLayer('baseline_sun');  setOverlayOn(true) }
      if (e.key === '4') { setShowBuildings(v => !v) }
      if (e.key === '5') { setShowTrees(v => !v) }
    }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [])

  // ── Building outlines layer (sim data: OSM=cyan, Overture=magenta) ──────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !site) return

    if (!showBuildings) {
      if (buildingsRef.current) {
        map.removeLayer(buildingsRef.current)
        buildingsRef.current = null
      }
      setBldgCount(null)
      return
    }

    let cancelled = false
    setBldgLoading(true)
    fetchSimBuildings(site.key, studySize).then(geojson => {
      if (cancelled || !mapRef.current) return
      if (buildingsRef.current) mapRef.current.removeLayer(buildingsRef.current)

      const nOsm = geojson.features.filter(f => f.properties?.source === 'osm').length
      const nOv  = geojson.features.filter(f => f.properties?.source === 'overture').length
      const nMs  = geojson.features.filter(f => f.properties?.source === 'ms').length
      setBldgCount({ osm: nOsm, overture: nOv, ms: nMs, total: geojson.features.length })

      buildingsRef.current = L.geoJSON(geojson, {
        style: bldgStyle,
        onEachFeature: (f, layer) => {
          const src = f.properties?.source ?? 'osm'
          const h   = f.properties?.height
          const parts = [src.toUpperCase()]
          if (h) parts.push(`h=${h}m`)
          layer.bindTooltip(parts.join(' \u00b7 '), { sticky: true, className: `bldg-tooltip bldg-tooltip-${src}` })
        },
      }).addTo(mapRef.current)
      setBldgLoading(false)
    }).catch(() => {
      if (!cancelled) setBldgLoading(false)
    })

    return () => { cancelled = true }
  }, [showBuildings, site, studySize])

  // ── Tree canopy layer ──────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !site) return

    if (!showTrees) {
      if (treesRef.current) {
        map.removeLayer(treesRef.current)
        treesRef.current = null
      }
      setTreeCount(null)
      return
    }

    let cancelled = false
    setTreeLoading(true)
    fetchTrees(site.key, studySize).then(geojson => {
      if (cancelled || !mapRef.current) return
      if (treesRef.current) mapRef.current.removeLayer(treesRef.current)

      const nOsm    = geojson.features.filter(f => f.properties?.source === 'osm').length
      const nGround = geojson.features.filter(f => f.properties?.source === 'ground').length
      setTreeCount({ osm: nOsm, ground: nGround, total: geojson.features.length })

      treesRef.current = L.geoJSON(geojson, {
        style: treeStyle,
        onEachFeature: (f, layer) => {
          const src  = f.properties?.source ?? 'osm'
          const kind = f.properties?.kind ?? ''
          const cr   = f.properties?.crown_radius
          const parts = [src.toUpperCase(), kind]
          if (cr) parts.push(`r=${cr}m`)
          layer.bindTooltip(parts.join(' \u00b7 '), { sticky: true, className: `tree-tooltip tree-tooltip-${src}` })
        },
      }).addTo(mapRef.current)
      setTreeLoading(false)
    }).catch(() => {
      if (!cancelled) setTreeLoading(false)
    })

    return () => { cancelled = true }
  }, [showTrees, site, studySize])

  if (!site) return null

  const color = gradeColor(site.grade_short)
  const ks    = site.key_stats ?? {}
  const legendBottom = 10 + (site.best_intervention ? 32 : 0) + (finance ? 27 : 0)

  return (
    <div className="city-map">

      {/* ── Top bar ── */}
      <div
        className="city-bar"
        style={{ borderLeftColor: color, cursor: 'pointer' }}
        onClick={() => { setSelectedBatch(null); setShowCard(s => !s) }}
        title="Show full score card"
      >
        <div className="city-grade" style={{ background: color }}>{site.grade_short}</div>

        <div className="city-meta">
          <span className="city-name">{site.name}</span>
          <span className="city-score" style={{ color }}>
            {site.composite_score.toFixed(0)}&nbsp;<span className="city-score-denom">/&nbsp;100</span>
          </span>
        </div>

        <div className="city-stats">
          <span>{ks.wind_mean_ms ?? '\u2014'} m/s</span>
          <span className="stat-dot">&middot;</span>
          <span>{ks.sun_mean_h_day ?? '\u2014'} h/day</span>
          <span className="stat-dot">&middot;</span>
          <span>{ks.utci_mean_c ?? '\u2014'}&deg;C UTCI</span>
        </div>

        {/* Layer selector */}
        <div className="city-layers" onClick={e => e.stopPropagation()}>
          {LAYER_KEYS.map((key, i) => {
            const isActive = activeLayer === key
            const isHidden = isActive && !overlayOn
            return (
              <button
                key={key}
                className={`layer-btn${isActive ? ' active' : ''}${isHidden ? ' layer-btn-off' : ''}`}
                style={isActive && overlayOn ? { borderColor: color, color } : {}}
                onClick={() => { isActive ? setOverlayOn(v => !v) : (setActiveLayer(key), setOverlayOn(true)) }}
                title={isActive
                  ? (overlayOn ? 'Hide overlay (click again to show)' : 'Show overlay')
                  : `${LAYER_LEGENDS[key].title} (shortcut: ${i + 1})`}
              >
                {LAYER_LABELS[key]}
              </button>
            )
          })}
          <button
            className={`layer-btn layer-btn-bldg${showBuildings ? ' active' : ''}`}
            style={showBuildings ? { borderColor: '#00e5ff', color: '#00e5ff' } : {}}
            onClick={() => setShowBuildings(v => !v)}
            title={`${showBuildings ? 'Hide' : 'Show'} building outlines \u2014 cyan=OSM, magenta=Overture (shortcut: 4)`}
          >
            {bldgLoading ? '\u2026' : 'Bldg'}
          </button>
          <button
            className={`layer-btn layer-btn-tree${showTrees ? ' active' : ''}`}
            style={showTrees ? { borderColor: '#66bb6a', color: '#66bb6a' } : {}}
            onClick={() => setShowTrees(v => !v)}
            title={`${showTrees ? 'Hide' : 'Show'} tree canopies (shortcut: 5)`}
          >
            {treeLoading ? '\u2026' : 'Trees'}
          </button>
        </div>

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

      {/* ── Building count badge ── */}
      {showBuildings && bldgCount && (
        <div className="bldg-badge">
          <span className="bldg-badge-osm">{bldgCount.osm} OSM</span>
          {bldgCount.overture > 0 && (
            <><span className="stat-dot">&middot;</span><span className="bldg-badge-ov">{bldgCount.overture} Overture</span></>
          )}
          {bldgCount.ms > 0 && (
            <><span className="stat-dot">&middot;</span><span className="bldg-badge-ms">{bldgCount.ms} MS</span></>
          )}
        </div>
      )}

      {/* ── Tree count badge ── */}
      {showTrees && treeCount && treeCount.total > 0 && (
        <div className="tree-badge" style={showBuildings && bldgCount ? { bottom: 34 } : {}}>
          {treeCount.osm > 0 && <span className="tree-badge-osm">{treeCount.osm} trees</span>}
          {treeCount.ground > 0 && (
            <><span className="stat-dot">&middot;</span><span className="tree-badge-ground">{treeCount.ground} zones</span></>
          )}
        </div>
      )}

      {/* ── Best intervention strip ── */}
      {site.best_intervention && (
        <div className="city-footer">
          <span className="footer-prefix">Best intervention</span>
          <span className="footer-label">[{site.best_intervention.key}] {site.best_intervention.label}</span>
          <span
            className="footer-gain"
            style={{ color: site.best_intervention.utci_improv_c >= 0 ? '#4caf50' : '#f44336' }}
          >
            UTCI {site.best_intervention.utci_improv_c >= 0 ? '+' : ''}
            {site.best_intervention.utci_improv_c?.toFixed(2)}&deg;C
          </span>
        </div>
      )}

      {/* ── Heatmap legend ── */}
      <div
        className="map-legend"
        style={{ bottom: legendBottom, opacity: overlayOn ? 1 : 0, transition: 'opacity 0.2s ease' }}
        aria-hidden="true"
      >
        <div className="map-legend-title">{LAYER_LEGENDS[activeLayer]?.title}</div>
        <div className="map-legend-bar" style={{ background: LAYER_LEGENDS[activeLayer]?.gradient }} />
        <div className="map-legend-ticks">
          <span>{LAYER_LEGENDS[activeLayer]?.lo}</span>
          <span>{LAYER_LEGENDS[activeLayer]?.hi}</span>
        </div>
      </div>

      {showCard && <ScoreCard item={{ ...site, _type: 'site' }} finance={finance} onClose={() => setShowCard(false)} />}
      {selectedBatch && <ScoreCard item={{ ...selectedBatch, _type: 'batch' }} onClose={() => setSelectedBatch(null)} />}

      {/* ── Finance strip ── */}
      {finance && (
        <div className="city-finance">
          <span className="finance-prefix">NPV</span>
          <span className="finance-npv">{fmtMoney(finance.npv_usd)}</span>
          <span className="stat-dot">&middot;</span>
          <span className="finance-roi" style={{ color: roiColor(finance.roi_pct) }}>
            {finance.roi_pct.toFixed(0)}% ROI
          </span>
          <span className="stat-dot">&middot;</span>
          <span className="finance-scenario">Scenario {finance.scenario_key}</span>
          {finance.stranded_rcp45 && (
            <span className="finance-stranded" title="Projected UTCI \u2265 46 \u00b0C by 2050 under RCP 4.5">
              \u26a0 Stranded 2050
            </span>
          )}
        </div>
      )}
    </div>
  )
}
