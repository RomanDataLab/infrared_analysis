# RenovationMap — Project Graph
> Last updated: 2026-06-01
> Status: Active development · All simulations complete (500 m + 1 km)

---

## 1. Idea

Municipalities face thousands of public spaces competing for renovation budgets, yet most prioritisation is based on visual inspection or age — not physical discomfort. **RenovationMap** answers a single question:

> *Where does the human body suffer most, and what is the cheapest fix?*

The tool runs four extreme-climate cities through a physics-based simulation pipeline and renders the results as an interactive 2 × 2 satellite dashboard. Every heatmap pixel represents a pedestrian-level thermal comfort value at street level, not a rooftop average. Intervention scenarios are tested automatically; the highest-impact option is surfaced as the renovation recommendation.

The four study neighbourhoods were chosen at the intersection of **highest real-estate pressure**, **active state investment pipelines**, and **zero existing thermal infrastructure** — conditions where a modest UTCI improvement of 2–4 °C translates directly into measurable dwell-time gain, reduced heat illness, and defensible public ROI.

---

## 2. Objectives

| # | Objective |
|---|-----------|
| 1 | Quantify pedestrian thermal discomfort at street level across four priority public-realm corridors |
| 2 | Test three intervention archetypes (tree planting, ground-material swap, shade canopy) per site and identify the highest-ROI option |
| 3 | Translate simulation results into a financial model (NPV / ROI) grounded in published literature |
| 4 | Render all outputs as a single-page interactive satellite dashboard usable without GIS expertise |
| 5 | Produce a reproducible Python pipeline that can be re-run for any site when the study polygon or API data is updated |
| 6 | Flag sites at risk of becoming pedestrian-hostile by 2050 under RCP 4.5 climate scenario |

---

## 3. Study Locations

### 3.1 Al-Murabba · Riyadh
| Field | Value |
|-------|-------|
| Coordinates | 24.692 °N, 46.709 °E |
| Climate | Desert heat |
| Analysis month | July (UTCI + solar), Shamal NW wind 6 m/s |
| Current grade | **F — Critical** (score 80.3 / 100) |
| Baseline UTCI | 46.79 °C mean daytime |
| Best intervention | 200 m canopy shade structure (Scenario D) |
| NPV / ROI | USD 967 K / **537 %** |
| Stranded 2050 | Yes — projected UTCI 48 °C under RCP 4.5 |

Historic royal district anchored by Al-Murabba Palace (1936). Borders the Diriyah Gate Development Authority (DGDA) zone — USD 50 bn UNESCO heritage-tourism megaproject. Land values 40–60 % above Riyadh average. State program: Riyadh DA "Historical Gateway District" designation, upgrades in procurement with no thermal KPI.

---

### 3.2 Masjid al-Haram surrounds · Mecca
| Field | Value |
|-------|-------|
| Coordinates | 21.427 °N, 39.814 °E |
| Climate | Desert heat |
| Analysis month | July (UTCI + solar), NW valley breeze 4 m/s |
| Current grade | **F — Critical** (score 84.8 / 100) |
| Baseline UTCI | 47.41 °C mean daytime |
| Best intervention | 200 m canopy shade structure (Scenario D) |
| NPV / ROI | USD 1.04 M / **520 %** |
| Stranded 2050 | Yes — projected UTCI 48.7 °C under RCP 4.5 |

Most visited site on Earth (~3 M pilgrims/week Hajj, ~8 M/month Umrah). Land above USD 40 000/m². Grand Mosque Expansion Project (2020–2030) demolishing ~1 block/year with no thermal modelling requirement. Abraj Al-Bait complex (601 m) creates wind shadow eliminating natural ventilation.

---

### 3.3 Dostyk–Medeu · Almaty
| Field | Value |
|-------|-------|
| Coordinates | 43.245 °N, 76.948 °E |
| Climate | Steppe cold |
| Analysis month | January (UTCI), December (solar), Siberian N-wind 10 m/s |
| Current grade | **A — Good** (score 4.0 / 100) |
| Baseline UTCI | −0.89 °C mean daytime |
| Best intervention | Asphalt → grass courtyard surface (Scenario B) |
| NPV / ROI | USD 80 K / **89 %** |
| Stranded 2050 | No |

Most prestigious commercial address in Central Asia. Residential land USD 3 000–5 500/m². Soviet passive-thermal grammar (wide boulevard + shaded courtyard + mature linden/poplar rows) being systematically dismantled by luxury infill since 2015. State program: "Comfortable City" master plan KZT 150 bn, 2022–2028.

---

### 3.4 Kenesary–Saryarka · Astana
| Field | Value |
|-------|-------|
| Coordinates | 51.160 °N, 71.407 °E |
| Climate | Steppe cold |
| Analysis month | January (UTCI), December (solar), steppe N-wind 12 m/s |
| Current grade | **D — Poor** (score 57.7) |
| Baseline UTCI | −28.15 °C mean daytime |
| Best intervention | Asphalt → grass courtyard surface (Scenario B) |
| NPV / ROI | USD 76 K / **63 %** |
| Stranded 2050 | No |

Junction of Kenesary Street and Saryarka Avenue — the commercial spine of Astana's Right Bank. Kenesary Street (1.8 km, NE–SW from railway station to Ishim River embankment) is the city's busiest pedestrian corridor: ground-floor retail, banking headquarters, mid-rise hotels, Central Bazaar cluster. Land values USD 1 200–2 000/m², rising 8–12 % annually ahead of the planned Astana LRT line. The Ishim River embankment (200 m south) provides the only significant green infrastructure in the district. State program: Astana City Development Corporation 2023–2027 renewal targeting Kenesary streetscape overhaul, no wind-speed or UTCI KPI in tender specs.

---

## 4. Methodology

```
Site polygons
  ├─ 500 × 500 m   study area (core public space)
  │    └─ Context polygon: 1 500 × 1 500 m
  └─ 1 000 × 1 000 m  analysis zone (district impact)
       └─ Context polygon: 1 400 m (1 km + 200 m buffer each side)

Data fetch — multi-source buildings
  ├─ OSM          (via Infrared SDK)  — primary source, good urban cores
  ├─ Overture Maps (via DuckDB)       — OSM + MS ML + Google Open Buildings
  └─ MS Building Footprints           — ML-derived from satellite imagery
        │
        └─ Spatial merge: IoU ≥ 0.10 dedup + containment removal
           → unified building set per site (merged_ids.json)
           → per-source coordinate reframing to analysis polygon centre

Vegetation — multi-source
  ├─ SDK vegetation (OSM tree points + ground cover zones)
  └─ Overture Maps tree canopy polygons
        → SDK-compatible Point features with height + crown_radius
        → sim_vegetation.json per site

Weather station
  └─ Nearest TMYx (EnergyPlus format, 2009-2023 average)
        └─ filter_weather_data → UTCI time-period slice

Baseline simulations  (512 × 512 grid, ~1 m/px)
  ├─ Wind speed       CFD, directional-blend merge, prevailing seasonal wind
  ├─ Direct sun hours  Geometry raycast, worst-case month
  └─ UTCI             Coupled radiation + convection + humidity, worst month

Scenario simulations  (re-run wind + UTCI with modified inputs)
  ├─ A  Tree planting          windbreak rows (cold) / shade grove (hot)
  ├─ B  Ground-material swap   asphalt → grass (cold) / pale concrete (hot)
  ├─ C  A + B combined
  └─ D  200 × 200 m canopy     flat-roof shade structure (hot sites only)

Scoring  (0–100 composite, three climate-specific metrics)
  Cold sites:  wind 35 % | solar 35 % | UTCI 30 %
  Hot sites:   wind 20 % | solar 35 % | UTCI 45 %
  Grades:  F >= 80 · E >= 65 · D >= 50 · C >= 35 · B >= 20 · A >= 0

Financial model  (25-year NPV, 8 % discount)
  ├─ Energy savings     ~2.5 % per °C UTCI improvement × local tariff
  ├─ Hedonic uplift     3–8 % property premium within 200 m
  ├─ Demand premium     5 % F&B / retail turnover uplift (5 % cap rate)
  └─ Climate risk       stranded-asset NPV (RCP 4.5, 15 % annual haircut)
```

### Grid alignment
API grid bounds are tile-snapped and can differ from the analytical polygon by 12–19 m on E/N edges. Bounds are saved per run in `baseline_bounds.json` and used for the Leaflet `imageOverlay` anchor, ensuring heatmap pixels land on the correct streets.

### Building footprint coordinate origins (CRS remapping)

The Infrared SDK, Overture enrichment, and Microsoft enrichment each store
building mesh vertices in local metres, but relative to **different origins**.
The simulation expects all buildings in analysis-polygon-SW frame. Per-source
reframing is applied before each run:

```
Source              Origin (SW corner of)        Reframe offset
──────────────────  ──────────────────────────── ─────────────────────────────
SDK / OSM           Context polygon              ctx_half - analysis_half
                      500 m analysis → 1 500 m     offset = 500 m
                      1 km  analysis → 2 000 m     offset = 500 m

Overture (ov_*)     500 m analysis polygon       250 - analysis_half
                    (fetch_overture.py)            500 m: 0 m  |  1 km: -250 m

MS Buildings (ms_*) 500 m analysis polygon       250 - analysis_half
                    (fetch_ms_buildings.py)        500 m: 0 m  |  1 km: -250 m
```

`_analysis_sw(lat_c, lon_c, size)` returns the SW corner of a square polygon
of side `size` centred on `(lat_c, lon_c)`:

```python
half_lat = (size / 2) / 111_320
half_lon = (size / 2) / (111_320 * cos(radians(lat_c)))
return lat_c - half_lat, lon_c - half_lon
```

Conversion back to WGS 84:

```python
lat = orig_lat + y / 111_320
lon = orig_lon + x / (111_320 * cos(radians(orig_lat)))
```

**Verification method:** the same physical building appears in both the 500 m
and 1 km `fetched_data.json`. Its local coordinates shift by exactly +250 m
in (x, y) between the two files, confirming a 250 m origin shift per step.
Using mismatched origins causes a visible ~500 m displacement on the map.

### Footprint polygon extraction (convex hull)

DotBimMesh buildings are stored as 3-D triangle meshes (vertices + face indices).
Extracting a clean 2-D footprint polygon requires three steps:

```
1. Ground-vertex extraction
   ─ Filter vertices where z ≤ z_min + 0.5 m
   ─ Deduplicate by snapping to 0.02 m grid  (SDK meshes duplicate
     vertices per face — same position appears 4–8× at different indices)

2. Convex hull  (Andrew's monotone chain, O(n log n))
   ─ Produces a guaranteed-simple, non-self-intersecting polygon
   ─ Handles compound buildings (multiple boxes), concave shapes, and
     degenerate triangulations without special-casing
   ─ Trade-off: concave notches (L / U shapes) are filled in, but the
     visual difference at map scale is negligible

3. WGS 84 projection
   ─ Convert hull vertices from local metres → (lon, lat) using the
     per-source origin (see CRS remapping table above)
   ─ Close ring (append first vertex)
```

**Why not boundary-edge tracing?** SDK meshes use per-face vertex duplication
and compound multi-box buildings, causing edge tracing to produce self-
intersecting polygons for ~11 % of OSM buildings. Angle-sort from centroid
fails on any concave shape. Convex hull achieves **0 % acute-angle polygons**
across all 4 636 buildings (Mecca 1 km) from all three sources.

### Priority-based spatial merge

Three building sources may contain duplicates of the same physical building.
Export-time merge deduplicates in WGS 84 using a grid-based spatial index:

```
Priority:   OSM (0)  >  Overture (1)  >  MS (2)

Algorithm:
  1. Sort all footprints by source priority (OSM first)
  2. For each building in priority order:
     a. Compute bounding box in WGS 84
     b. Query grid index for nearby accepted buildings
     c. If bbox IoU ≥ 0.10 with any accepted building → skip (duplicate)
     d. Otherwise → accept + insert into grid index
  3. Pass 2 — containment removal:
     a. Sort accepted buildings by bbox area (largest first)
     b. For each building, query grid for overlapping neighbours
     c. If a smaller building's bbox is fully inside a larger one → remove it
     (catches courtyard artefacts, mesh sub-parts, and MS fills inside OSM)
  4. Save per-source GeoJSON (buildings_osm / _overture / _ms.geojson)
     for rollback capability
  5. Output accepted features as unified buildings.geojson
  6. Save merged_ids.json → used by baseline.py to filter fetched_data
     buildings so that simulation uses exactly the same set shown on the map

Grid cell size: 0.0005° (~55 m) — balances lookup speed vs memory
IoU threshold: 0.10 — tuned to eliminate all visible overlaps
  (0.25 left ~200 pairs; 0.15 left ~80; 0.10 → 0 pairs with IoU ≥ 10 %)
```

Typical results (Mecca 1 km):

```
4 636 raw  →  3 559 merged
  IoU dedup removed:   813 (118 OSM, 609 Overture, 86 MS)
  containment removed: 264 (179 OSM, 3 Overture, 82 MS)
```

Fetch-time dedup (in `fetch_overture.py` / `fetch_ms_buildings.py`) catches
most duplicates, but operates in mixed local-coordinate spaces. The export-
time merge in WGS 84 catches residual overlaps, especially Overture buildings
whose fetch-time dedup used a mismatched coordinate origin for 1 km analysis.

### Tree canopy extraction

Two sources provide tree/vegetation geometry for the frontend overlay:

```
Source 1 — OSM tree points:
  ─ Read vegetation dict from fetched_data.json (Point features)
  ─ Estimate crown radius:
      • diameter_crown / 2  (if available, usually absent)
      • height × 0.4        (allometric, if height tag exists)
      • default: 4 m        (fallback)
  ─ Generate 24-vertex circular polygon in WGS 84

Source 2 — Ground-material vegetation zones:
  ─ Read ground_materials.vegetation from fetched_data.json
  ─ Filter: class ∈ {wood, park, grass} or type ∈ {forest, grassland, …}
  ─ Strip Z coordinates, simplify with Ramer-Douglas-Peucker (ε = 0.00005°)
  ─ Split MultiPolygon → individual Polygon features

Post-processing (4 sequential passes):
  1. Containment removal: small canopies fully inside larger zones -> removed
     (SpatialGrid + bbox containment check, same as building pipeline)
  2. Merge overlapping: unary_union all tree polygons, explode MultiPolygon
     back to individual features. Classify by area: <200 m2 = tree, else zone.
     Eliminates all polygon overlaps (verified: 0 overlapping pairs).
  3. Building subtraction: load buildings.geojson, build Shapely STRtree
     - shapely.difference(tree, building) for each overlap
     - Drop features fully inside buildings
     - Split MultiPolygon results into individual features
  4. Road subtraction: fetch OSM highway centerlines via Overpass API
     - Buffer each road by half-width based on highway type:
       motorway 15m, primary 10m, secondary 8m, residential 5m
     - Merge all road buffers with unary_union
     - shapely.difference(tree, road) for each overlap
     - Roads cached locally in analysis/cache/roads/
```

Typical results (Almaty 1 km):
  2 263 raw -> 876 merged -> 458 after building + road clip
  213 clipped by buildings, 30 fully inside buildings
  101 clipped by roads, 401 fully on roads

Script: `analysis/export_trees_geojson.py`

### Simulation–map alignment

To ensure heatmap pixels align with building outlines on the map:
1. `merged_ids.json` from the export pipeline filters `fetched_data.json`
   buildings so the simulation uses exactly the deduped set shown under "Bldg"
2. `sim_vegetation.json` converts tree canopy polygons to SDK Point features
   so the simulation uses the same trees shown under "Trees"
3. Per-source coordinate reframing (`_reframe_buildings()` in baseline.py)
   translates OSM, Overture, and MS buildings to the analysis polygon frame

### Output files per site

```
analysis/results/{site}[/1km]/
  ├─ fetched_data.json            ← cached API response (buildings, veg, ground, station UUID)
  ├─ merged_ids.json              ← building IDs that passed spatial dedup
  ├─ sim_vegetation.json          ← SDK-compatible tree Point features for simulation
  ├─ baseline_stats.json          ← wind/sun/utci summary statistics
  ├─ baseline_bounds.json         ← tile-snapped grid extents for map overlay
  ├─ baseline_*.npy               ← raw 512×512 grids
  └─ baseline_*.png               ← heatmap images

public/heatmaps/{site}[/1km]/
  ├─ buildings.geojson             ← merged (served to frontend)
  ├─ buildings_osm.geojson         ← OSM only (pre-merge, for rollback)
  ├─ buildings_overture.geojson    ← Overture only
  ├─ buildings_ms.geojson          ← Microsoft only
  ├─ trees.geojson                 ← tree canopies + vegetation zones
  ├─ baseline_wind.png / _overlay.png
  ├─ baseline_sun.png / _overlay.png
  └─ baseline_utci.png / _overlay.png
```

---

## 5. Data Sources

| Source | Used for | Notes |
|--------|----------|-------|
| **Infrared City API v2** | Wind CFD, solar raycast, UTCI simulation, building fetch, vegetation fetch, ground materials, weather station | Core compute engine |
| **OpenStreetMap** (via Infrared) | Building footprints, tree positions, ground cover | Primary building dataset — insufficient coverage in Central/West Asia |
| **Overture Maps** (via `fetch_overture.py`) | Additional building footprints not in OSM | Merged from OSM + Microsoft ML + Google Open Buildings; adds ~57 % more buildings for Riyadh |
| **Microsoft Building Footprints** (via `fetch_ms_buildings.py`) | ML-derived building footprints from Bing imagery | 1.4 B buildings globally; high recall for smaller structures; CDLA Permissive 2.0 license |
| **Overture Maps vegetation** | Tree canopy polygons for frontend + simulation | Converted to SDK Point features with height/crown_radius |
| **EnergyPlus TMYx 2009-2023** (via Infrared weather API) | UTCI weather data per site | KAZ_AKM_Astana.351880, SAU stations for Riyadh/Mecca |
| **Mapbox Satellite** | Basemap tiles | Token via `VITE_MAPBOX_TOKEN` env var |
| **Donovan & Butry (2010)** | Hedonic uplift coefficient — trees to property value | Ref [3] |
| **Sander et al. (2010)** | Hedonic uplift — urban greenery | Ref [4] |
| **Bowler et al. (2010)** | Urban cooling effect of trees | Ref [5] |
| **Caldecott (2017)** | Stranded-asset NPV methodology | Ref [8] |
| **Local electricity tariffs** | Energy-saving monetisation | SAR 0.048/kWh · KZT 19–25/kWh |

---

## 6. Tools & Stack

### Frontend
| Tool | Role |
|------|------|
| **React 18** | Single-page app framework |
| **Leaflet + react-leaflet** | Interactive satellite maps, `imageOverlay` for heatmaps |
| **Mapbox Satellite v9** | Basemap tiles (best OSM alignment for Middle East / Central Asia) |
| **Vite** | Build + dev server |
| **CSS (custom)** | Dark UI, 2 × 2 grid layout, project modal, financial panel |

### Python Pipeline
| Script | Role |
|--------|------|
| `sites.py` | Site definitions — polygons (500 m + 1 km), weather params, scenario configs |
| `baseline.py` | Steps 1–6: fetch data → run wind/solar/UTCI → save stats + heatmaps. Supports `--cached` (skip API fetch) and `--buffer` (context buffer size) flags |
| `scenarios.py` | Re-run wind + UTCI for scenarios A / B / C per site |
| `canopy_scenario.py` | Scenario D — 200 × 200 m flat-roof shade canopy (hot sites) |
| `score.py` | Composite 0–100 score + grade from baseline + scenario stats |
| `export_web.py` | Bundle all results into `public/renovation_data.json` + `financial_data.json` |
| `fetch_overture.py` | Enrich OSM buildings with Overture Maps via DuckDB spatial join |
| `fetch_ms_buildings.py` | Enrich with Microsoft Global ML Building Footprints (1.4 B worldwide) |
| `export_buildings_geojson.py` | Convert DotBimMesh → WGS 84 GeoJSON, spatial merge, save `merged_ids.json` |
| `export_trees_geojson.py` | Tree canopy pipeline (OSM + ground veg + Overture), save `sim_vegetation.json` |
| `climate_financial_model.py` | Four-layer NPV / ROI model |
| `generate_financial_data.py` | Write `financial_data.json` / `financial_data_1km.json` from model outputs |
| `batch.py` | Run full pipeline for all sites sequentially |
| `refine.py` | Detect stale results and trigger selective re-runs |
| `regen_overlays.py` | Regenerate PNG overlays from cached `.npy` grids without API calls |

### External Services
| Service | Purpose |
|---------|---------|
| **Infrared City API** (https://api.infrared.city/v2) | All simulation compute |
| **Overture Maps** (DuckDB spatial query) | Building + vegetation enrichment |
| **Microsoft Building Footprints** (Azure blob) | ML-derived footprints |

---

## 7. Architecture

```
infrared/
├── src/                          # React frontend
│   ├── App.jsx                   # Root: 2×2 grid, toolbar, modals, project idea
│   ├── App.css                   # All styles
│   └── components/
│       ├── CityMap.jsx           # Leaflet map + heatmap overlay + building/tree layers
│       ├── ScoreCard.jsx         # Per-site score card (grade, components, interventions)
│       └── FinancialPanel.jsx    # NPV / ROI panel with value layer breakdown
│
├── public/
│   ├── renovation_data.json      # All simulation results + metadata (generated)
│   ├── financial_data.json       # NPV / ROI per site — 500 m (generated)
│   ├── financial_data_1km.json   # NPV / ROI per site — 1 km (generated)
│   └── heatmaps/
│       ├── riyadh/[1km/]         # baseline_wind/sun/utci + overlays + buildings + trees
│       ├── mecca/[1km/]
│       ├── almaty/[1km/]
│       └── astana/[1km/]
│
├── analysis/                     # Python pipeline
│   ├── sites.py                  # Site config (500 m + 1 km polygons, weather, scenarios)
│   ├── baseline.py               # Step 1: data fetch + 3 baseline analyses (--cached, --buffer)
│   ├── scenarios.py              # Step 2: scenario A/B/C simulations
│   ├── canopy_scenario.py        # Step 2b: scenario D (canopy, hot sites)
│   ├── score.py                  # Step 3: scoring + grades
│   ├── export_web.py             # Step 4: bundle to public/
│   ├── fetch_overture.py         # Building enrichment (Overture Maps)
│   ├── fetch_ms_buildings.py     # Building enrichment (Microsoft ML)
│   ├── export_buildings_geojson.py  # DotBimMesh → GeoJSON + spatial merge
│   ├── export_trees_geojson.py   # Tree canopy → GeoJSON + sim_vegetation.json
│   ├── climate_financial_model.py
│   ├── generate_financial_data.py
│   ├── batch.py
│   ├── refine.py
│   ├── regen_overlays.py
│   ├── cache/                    # Cached Overture/MS/road data
│   └── results/
│       ├── riyadh/[1km/]         # baseline_stats.json, merged_ids.json, sim_vegetation.json,
│       ├── mecca/[1km/]          #   fetched_data.json, baseline_bounds.json, *.npy, *.png
│       ├── almaty/[1km/]
│       └── astana/[1km/]
│
├── .env                          # VITE_MAPBOX_TOKEN, INFRARED_API_KEY (gitignored)
└── graph.md                      # This file
```

### Data flow
```
sites.py
  |
  v
baseline.py --> results/{site}/fetched_data.json   (buildings, veg, ground mats; cached)
            --> results/{site}/baseline_*.npy       (raw 512x512 grids)
            --> results/{site}/baseline_*.png       (heatmap images)
            --> results/{site}/baseline_bounds.json (tile-snapped extents)
            --> results/{site}/baseline_stats.json
  |
  v                                ┌─ merged_ids.json (building filter)
fetch_overture.py ─┐               │
fetch_ms_buildings ┤               │
export_buildings ──┴──> buildings.geojson ──> merged_ids.json
export_trees ─────────> trees.geojson ──────> sim_vegetation.json
                                   │
                                   └─ baseline.py --cached reads these
                                      to align simulation with map layers
  |
  v
scenarios.py      --> results/{site}/scenario_*_utci/wind.npy + .png
canopy_scenario.py (hot sites)
                  --> results/{site}/scenarios_summary.json
  |
  v
score.py --> results/{site}/courtyard_score.json
  |
  v
export_web.py              --> public/renovation_data.json
generate_financial_data.py --> public/financial_data.json + financial_data_1km.json
                           --> public/heatmaps/{site}/*.png
```

---

## 8. Progress

### Completed

| Task | Notes |
|------|-------|
| React + Leaflet 2×2 grid scaffold | CityMap component, heatmap imageOverlay |
| `baseline.py` full pipeline | Wind / solar / UTCI for all 4 sites (500 m + 1 km) |
| `scenarios.py` A/B/C for all sites | |
| `score.py` + `export_web.py` | Composite scoring + web export |
| Almaty windbreak — 3-row birch, N edge, 920 m wide | |
| Riyadh shade grove — 513 date palms (9 × 57 grid) | |
| Astana windbreak — 3-row elm + veg bug fix | |
| Mecca shade grove — 513 date palms + veg bug fix | |
| Mecca Scenario D — 200 × 200 m canopy | |
| **Multi-source building pipeline** | OSM + Overture + MS footprints, spatial merge with IoU dedup + containment removal |
| **Tree canopy pipeline** | OSM + ground veg + Overture → trees.geojson + sim_vegetation.json |
| **Per-source CRS reframing** | Fixed coordinate origin mismatch between OSM, Overture, MS buildings |
| **1 km simulations** | All 4 sites at 1000 × 1000 m with 200 m buffer, using merged buildings + trees |
| **Simulation–map alignment** | merged_ids.json + sim_vegetation.json ensure heatmaps match building/tree overlays |
| Financial panel — 4-layer NPV model | Energy, hedonic, demand premium, climate risk |
| **Financial tooltips** | Hover tooltips for ROI, NPV, Capex, Hedonic uplift, Demand premium, Climate risk avoided, Stranded risk, ΔUTCI, GFA |
| Toolbar — Lock Map, Project modal, Finance modal | |
| Toolbar — 500 m / 1 km size toggle | Both scales fully simulated |
| Project modal — sticky close button | flex column + scroll wrapper |
| Project modal — neighbourhood selection rationale | Price, demand, gentrification, state programs |
| Project modal — per-location detail cards | |
| **Project Idea — methodology update** | Multi-source building pipeline, two analysis scales, vegetation sourcing |
| **Astana neighbourhood rename** | Kenesary St / Saryarka Ave / Ishim River (matches actual simulated area) |
| **Mapbox token to env var** | Removed hardcoded token from source code; `VITE_MAPBOX_TOKEN` in `.env` |
| Mapbox Satellite basemap | Best OSM alignment for Middle East / Central Asia |

### Known Issues

| Issue | Status |
|-------|--------|
| Ground materials HTTP 500 from Infrared (Mapbox source) | Fallback in place — pipeline continues without surface data |
| Demand premium uses default market assumptions (5 % cap rate, 3 % rental uplift) | Noted in tooltip; calibrate with local listing data |
| `postprocess_ndvi.py` removed from pipeline | Was for NDVI-derived canopy; replaced by Overture tree pipeline |

---

## 9. Current Simulation Results

### 500 m — Study Area

| City | Grade | Score | UTCI | Wind | Sun | Best Intervention | NPV | ROI |
|------|-------|-------|------|------|-----|-------------------|-----|-----|
| **Mecca** | F | 84.8 | 47.41 °C | 2.03 m/s | 10.25 h/d | 200 m canopy (D) | $1.04 M | 520 % |
| **Riyadh** | F | 80.3 | 46.79 °C | 2.74 m/s | 9.86 h/d | 200 m canopy (D) | $967 K | 537 % |
| **Astana** | D | 57.7 | −28.15 °C | 5.75 m/s | 6.11 h/d | Asphalt → grass (B) | $76 K | 63 % |
| **Almaty** | A | 4.0 | −0.89 °C | 2.90 m/s | 5.87 h/d | Asphalt → grass (B) | $80 K | 89 % |

### 1 km — Analysis Zone

1 km simulations use merged multi-source buildings and Overture tree vegetation. Financial model scales floor area 4× and capex 3.5× from 500 m baseline. Results available in `financial_data_1km.json`.

---

## 10. API Token Usage

| Run | Tokens | Notes |
|-----|--------|-------|
| 500 m baselines + scenarios (4 sites × wind/solar/UTCI + A/B/C/D) | 6 240 | Initial pipeline — all 4 sites at 500 × 500 m |
| 1 km baselines (4 sites × wind/solar/UTCI, merged buildings + trees) | 10 000 | Re-simulated at 1000 × 1000 m with 200 m buffer |
| **Total** | **16 240** | https://app.infrared.city/account |

---

## 11. Scoring Reference

```
Composite score = sum(metric_normalised × weight)

metric_normalised = (raw - best_reference) / (worst_reference - best_reference) × 100

Cold sites                       Hot sites
  wind:  frac > 5 m/s              wind:  frac < 1 m/s
  solar: frac < 1 h/day (Dec)      solar: frac > 5 h/day (Jul)
  utci:  frac < -13 °C (Jan)       utci:  frac > +38 °C (Jul)

Weights
  cold:  wind 35 % | solar 35 % | utci 30 %
  hot:   wind 20 % | solar 35 % | utci 45 %

Grade thresholds
  F  >= 80   Critical — fix immediately
  E  >= 65   Severe   — high renovation priority
  D  >= 50   Poor     — include in next cycle
  C  >= 35   Moderate — improvements recommended
  B  >= 20   Fair     — minor enhancements worthwhile
  A  >=  0   Good     — no urgent intervention needed
```
