# RenovationMap — Project Graph
> Last updated: 2026-05-30  
> Status: Active development · Infrared API outage in progress (Astana re-run pending)

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
| NPV / ROI | USD 1.33 M / **741 %** |
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
| NPV / ROI | USD 2.25 M / **1 126 %** |
| Stranded 2050 | Yes — projected UTCI 48 °C under RCP 4.5 |

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
| NPV / ROI | USD 79.7 K / **89 %** |
| Stranded 2050 | No |

Most prestigious commercial address in Central Asia. Residential land USD 3 000–5 500/m². Soviet passive-thermal grammar (wide boulevard + shaded courtyard + mature linden/poplar rows) being systematically dismantled by luxury infill since 2015. State program: "Comfortable City" master plan KZT 150 bn, 2022–2028.

---

### 3.4 Bayterek / Nurzhol Boulevard · Astana
| Field | Value |
|-------|-------|
| Coordinates | 51.128 °N, 71.430 °E *(corrected 2026-05-29 — prior run was ~3.6 km north of Bayterek)* |
| Climate | Steppe cold |
| Analysis month | January (UTCI), December (solar), steppe N-wind 12 m/s |
| Current grade | **D — Poor** (score 58.9) *(from prior incorrect coordinates — re-run pending)* |
| Baseline UTCI | −28.13 °C *(prior coords — figure will update on re-run)* |
| Best intervention | Asphalt → grass courtyard surface (Scenario B) *(prior coords)* |
| NPV / ROI | USD 75.3 K / **63 %** *(prior coords)* |
| Stranded 2050 | No |

Ceremonial spine of Kazakhstan's purpose-built capital (Nurzhol Blvd, master-planned by Kisho Kurokawa, complete ~2006). Entire corridor state-owned — no acquisition barriers. Mean January air temp −17 °C, northerlies 10–14 m/s. State program: Astana City Development Corporation 2023–2027 renewal (marble paving + lighting only, no thermal KPI).

---

## 4. Methodology

```
Site polygon (500 m × 500 m)
  └─ Context polygon (1 500 m × 1 500 m)
        ├─ Buildings fetch   (OSM via Infrared API + Overture Maps enrichment)
        ├─ Vegetation fetch  (OSM; < 10 trees → defer to API internal dataset)
        └─ Ground materials  (Mapbox source; fallback: skip if API 500)

Weather station
  └─ Nearest TMYx (EnergyPlus format, 2009-2023 average)
        └─ filter_weather_data → UTCI time-period slice

Baseline simulations  (512 × 512 grid, ~1 m/px)
  ├─ Wind speed       CFD, directional-blend merge, prevailing seasonal wind
  ├─ Direct sun hours Geometry raycast, worst-case month
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
  ├─ Demand premium     5 % F&B / retail turnover uplift
  └─ Climate risk       stranded-asset NPV (RCP 4.5, 15 % annual haircut)
```

### Grid alignment
API grid bounds are tile-snapped and can differ from the analytical polygon by 12–19 m on E/N edges. Bounds are saved per run in `baseline_bounds.json` and used for the Leaflet `imageOverlay` anchor, ensuring heatmap pixels land on the correct streets.

---

## 5. Data Sources

| Source | Used for | Notes |
|--------|----------|-------|
| **Infrared City API v2** | Wind CFD, solar raycast, UTCI simulation, building fetch, vegetation fetch, ground materials, weather station | Core compute engine |
| **OpenStreetMap** (via Infrared) | Building footprints, tree positions, ground cover | Primary building dataset |
| **Overture Maps** (via `fetch_overture.py`) | Additional building footprints not in OSM | Enrichment layer; adds ~57 % more buildings for Riyadh |
| **EnergyPlus TMYx 2009-2023** (via Infrared weather API) | UTCI weather data per site | KAZ_AKM_Astana.351880, SAU stations for Riyadh/Mecca |
| **Mapbox** (via Infrared ground-material API) | Asphalt / concrete / grass / soil / water layers | Currently returning HTTP 500 — fallback: skip |
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
| **Vite** | Build + dev server |
| **CSS (custom)** | Dark UI, 2 × 2 grid layout, project modal |

### Python Pipeline
| Script | Role |
|--------|------|
| `sites.py` | Site definitions — polygons, weather params, scenario configs |
| `baseline.py` | Steps 1–6: fetch data → run wind/solar/UTCI → save stats + heatmaps |
| `scenarios.py` | Re-run wind + UTCI for scenarios A / B / C per site |
| `canopy_scenario.py` | Scenario D — 200 × 200 m flat-roof shade canopy (hot sites) |
| `score.py` | Composite 0–100 score + grade from baseline + scenario stats |
| `export_web.py` | Bundle all results into `public/renovation_data.json` + `financial_data.json` |
| `fetch_overture.py` | Enrich OSM buildings with Overture Maps via DuckDB spatial join |
| `climate_financial_model.py` | Four-layer NPV / ROI model |
| `generate_financial_data.py` | Write `financial_data.json` from model outputs |
| `batch.py` | Run full pipeline for all sites sequentially |
| `refine.py` | Detect stale results and trigger selective re-runs |
| `regen_overlays.py` | Regenerate PNG overlays from cached `.npy` grids without API calls |
| `postprocess_ndvi.py` | Convert NDVI-derived canopy points to `ndvi_trees.json` |

### External Services
| Service | Purpose |
|---------|---------|
| **Infrared City API** (https://api.infrared.city/v2) | All simulation compute |
| **Overture Maps** (DuckDB spatial query) | Building enrichment |

---

## 7. Architecture

```
infrared/
├── src/                          # React frontend
│   ├── App.jsx                   # Root: 2×2 grid, toolbar, modals
│   ├── App.css                   # All styles
│   └── components/
│       ├── CityMap.jsx           # Leaflet map + heatmap overlay + scenario pins
│       └── FinancialPanel.jsx    # NPV / ROI strip per site
│
├── public/
│   ├── renovation_data.json      # All simulation results + metadata (generated)
│   ├── financial_data.json       # NPV / ROI per site (generated)
│   └── heatmaps/
│       ├── riyadh/               # baseline_wind/sun/utci + scenario overlays
│       ├── mecca/
│       ├── almaty/
│       └── astana/
│
├── analysis/                     # Python pipeline
│   ├── sites.py                  # Site config (polygons, weather, scenarios)
│   ├── baseline.py               # Step 1: data fetch + 3 baseline analyses
│   ├── scenarios.py              # Step 2: scenario A/B/C simulations
│   ├── canopy_scenario.py        # Step 2b: scenario D (canopy, hot sites)
│   ├── score.py                  # Step 3: scoring + grades
│   ├── export_web.py             # Step 4: bundle to public/
│   ├── fetch_overture.py         # Building enrichment helper
│   ├── climate_financial_model.py
│   ├── generate_financial_data.py
│   ├── batch.py
│   ├── refine.py
│   ├── regen_overlays.py
│   ├── postprocess_ndvi.py
│   └── results/
│       ├── riyadh/               # baseline_stats.json, scenarios_summary.json,
│       ├── mecca/                #   courtyard_score.json, fetched_data.json,
│       ├── almaty/               #   baseline_bounds.json, *.npy grids, *.png
│       └── astana/
│
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
  v
scenarios.py      --> results/{site}/scenario_*_utci/wind.npy + .png
canopy_scenario.py (hot sites)
                  --> results/{site}/scenarios_summary.json
  |
  v
score.py --> results/{site}/courtyard_score.json
  |
  v
export_web.py          --> public/renovation_data.json
generate_financial_data.py --> public/financial_data.json
                       --> public/heatmaps/{site}/*.png
```

---

## 8. Progress

### Completed

| Task | Notes |
|------|-------|
| React + Leaflet 2×2 grid scaffold | CityMap component, heatmap imageOverlay |
| `baseline.py` full pipeline | Wind / solar / UTCI for all 4 sites |
| `scenarios.py` A/B/C for all sites | |
| `score.py` + `export_web.py` | Composite scoring + web export |
| Almaty windbreak — 3-row birch, N edge, 920 m wide | |
| Riyadh shade grove — 513 date palms (9 × 57 grid) | |
| Astana windbreak — 3-row elm + veg bug fix | |
| Mecca shade grove — 513 date palms + veg bug fix | |
| Mecca Scenario D — 200 × 200 m canopy | |
| Overture Maps enrichment re-run — Riyadh, Almaty, Mecca | +57 % more buildings for Riyadh |
| Financial panel — 4-layer NPV model | |
| Toolbar — Lock Map, Project modal, Finance modal | |
| Toolbar — 500 m / 1 km size toggle (pill buttons) | Frontend only; 1 km simulations pending API recovery |
| Removed Zoom All button | React.useState crash; button redundant |
| Project modal — sticky close button | flex column + scroll wrapper |
| Project modal — merged Sources + Links sections | |
| Project Idea — neighbourhood selection rationale | Price, demand, gentrification, state programs |
| Project Idea — per-location detail cards (`pm-location`) | |
| **Astana coordinate fix** (2026-05-29) | Corrected from 51.161 N / 71.406 E → 51.128 N / 71.430 E |
| `baseline.py` hardened against weather API outage | Wind + solar complete even when weather endpoint is 500; UUID cached |

### In Progress

| Task | Blocker |
|------|---------|
| Astana baseline re-run at correct Bayterek coordinates | **Infrared API broadly down** — `/gis/vegetation`, `/ground-material/collect`, `/weather/location`, `check_area_state` all HTTP 500. Buildings cached (760 OSM + Overture). |

### Pending (after API recovers)

```bash
# Astana — correct coordinates
python baseline.py  --site astana
python scenarios.py --site astana
python score.py     --site astana
python export_web.py

# Then update App.jsx modal:
#   replace "Grade pending re-run" with actual grade
#   update UTCI figure in Astana location description

# Optional — 1 km polygon runs for all sites
python baseline.py  --site riyadh && python scenarios.py --site riyadh
python baseline.py  --site mecca  && python scenarios.py --site mecca
python baseline.py  --site almaty && python scenarios.py --site almaty
python score.py --site riyadh && python score.py --site mecca && python score.py --site almaty
python export_web.py
```

### Known Issues

| Issue | Status |
|-------|--------|
| Astana heatmaps in app still from wrong coordinates (51.161 N) | Blocked on API |
| 1 km polygon simulations not yet run (study area expanded in code only) | Waiting for API recovery |
| Ground materials always HTTP 500 from Infrared (Mapbox source) | Fallback in place — pipeline continues without surface data |
| Vegetation fetch HTTP 500 for Astana new coords | Fallback: 0 trees → API uses internal dataset |

---

## 9. Current Simulation Results

| City | Grade | Score | UTCI | Wind | Sun | Best Intervention | NPV | ROI |
|------|-------|-------|------|------|-----|-------------------|-----|-----|
| **Mecca** | F | 84.8 | 47.41 °C | 2.03 m/s | 10.25 h/d | 200 m canopy (D) | $2.25 M | 1 126 % |
| **Riyadh** | F | 80.3 | 46.79 °C | 2.74 m/s | 9.86 h/d | 200 m canopy (D) | $1.33 M | 741 % |
| **Astana** | D* | 58.9* | −28.13 °C* | 6.19 m/s | 6.25 h/d | Asphalt → grass (B) | $75.3 K | 63 % |
| **Almaty** | A | 4.0 | −0.89 °C | 2.90 m/s | 5.87 h/d | Asphalt → grass (B) | $79.7 K | 89 % |

*Astana figures from prior incorrect coordinates — re-run pending.*

---

## 10. Scoring Reference

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
