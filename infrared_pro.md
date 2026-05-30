# Product B: RenovationMap
### Climate-Driven Portfolio Triage for Existing Real Estate Stock

---

## 1. Product Description

**RenovationMap** is a spatial prioritization platform that tells municipalities, real estate funds, and renovation contractors *which buildings and courtyards to fix first* — based on simulated microclimate data, not political or administrative logic.

It ingests a district polygon, batch-runs wind and thermal comfort analyses across all courtyards and open spaces, and outputs a ranked intervention map: where the worst wind tunneling is, which buildings mutually shadow each other in winter, which ground surface changes yield the biggest thermal comfort gain per unit of spend.

### Primary Geographies
- **Almaty, Kazakhstan** — Soviet-era mikrorayon panel blocks (khrushchevki, brezhnevki). Courtyards are wind traps, buildings shadow each other in winter, national renovation program allocates hundreds of millions with no spatial logic.
- **Riyadh, Saudi Arabia** — Aging compounds and mid-century residential stock where outdoor amenity zones (pools, terraces, pedestrian approaches) are thermally unusable 6+ months/year. Vision 2030 drives massive retrofit and new development activity.

### Core User Problem
Renovation budgets are allocated by building age, political priority, or first-come-first-served. No one currently asks: *which spaces have the worst microclimate drag on livability and yield?* RenovationMap answers that question with physics-based simulation at ~1m resolution.

### What It Produces
- Heatmap overlay of UTCI thermal stress + wind exposure across a district
- Ranked list of courtyards/spaces by severity score
- Before/after scenario modeling: add tree row → delta comfort score; change ground surface → thermal impact; infill building gap → wind reduction vs. solar tradeoff
- Intervention priority map with quantified comfort gain per intervention
- Export-ready PDF report for municipal budget submissions

---

## 2. Target Customers

| Segment | Geography | Buyer Title |
|---|---|---|
| Municipal government | Almaty | Head of Urban Development / Akimat infrastructure dept. |
| National renovation program | Kazakhstan | KazSvyazService / Ministry of Industry and Infrastructure |
| Real estate investment fund | Almaty | Portfolio manager, asset director |
| Saudi national housing bodies | Riyadh | REDF, National Housing Company, PIF-linked developers |
| Renovation contractors | Both cities | Business development / tender teams |

---

## 3. Technical Architecture

### Core Analysis Engine
- **Infrared.city Python SDK** — primary simulation engine
  - `thermal-comfort-index` (UTCI) — outdoor heat/cold stress maps
  - `thermal-comfort-statistics` — % of time in heat/cold stress by zone
  - `wind-speed` — pedestrian-level wind magnitude (8-direction sweep)
  - `pedestrian-wind-comfort` — Lawson/VDI/Davenport comfort classification
  - `direct-sun-hours` — winter solar access per courtyard (critical for Almaty)
  - `sky-view-factors` — sky openness, affects both daylight and thermal radiation
- Async batch processing with webhook callbacks (`run_area()` + `merge_area_jobs()`)
- Directional blend merge strategy for wind seam elimination across tiles
- Cost preview before every run (`client.preview_area_cost()`)

### Geospatial Input Layer
- `osmnx` — pull building footprints, heights, street networks from OpenStreetMap
- `geopandas` + `shapely` — polygon construction, courtyard boundary extraction
- `pyproj` — coordinate transformation to WGS84 before SDK submission
- `overpy` — OSM Overpass API for tree locations and ground surface types
- ERA5 (Copernicus) — historical hourly climate reanalysis for multi-year UTCI stats
- OpenWeatherMap / Visual Crossing — live weather station data feed

### Raster Processing Layer
- `numpy` — native SDK output format (2D masked arrays per analysis)
- `rasterio` — georeference arrays, export GeoTIFF, reproject to local CRS
- `xarray` — stack UTCI arrays across 12 months into labeled 4D composite
- `scipy.ndimage` — spatial smoothing, local statistics on comfort grids
- `scikit-image` — zone segmentation: identify contiguous stress/comfort regions

### Scoring & Optimization
- **Composite severity score** per courtyard cell:
  ```
  SeverityScore = w1*UTCI_stress_pct + w2*wind_discomfort_pct + w3*(1 - winter_sun_hours_normalized)
  ```
  Weights tuned per city: Almaty emphasizes winter sun + wind; Riyadh emphasizes summer UTCI
- `scikit-learn` — regression model mapping intervention type → expected delta score
- Greedy optimization: rank interventions by (delta_score / estimated_cost)
- Intervention scenario re-run: modify geometry/materials → re-submit to SDK → delta heatmap

### Backend
- `FastAPI` — REST API: POST polygon → async job → GET results
- `Celery` + `Redis` — job queue for SDK analysis tasks (30–120s per run)
- `PostgreSQL` + `PostGIS` — spatial storage of results, parcel linkage
- `SQLAlchemy` — ORM
- `boto3` / S3 — large payload storage (SDK BigPayloadError handler)
- `pydantic` — request/response validation (consistent with SDK internals)

### Visualization & Reporting
- `pydeck` — primary interactive heatmap (web-ready, handles 1M+ cells)
- `Mapbox GL JS` — base map with satellite imagery for Almaty/Riyadh context
- `plotly` — intervention comparison charts, before/after bar charts
- `WeasyPrint` / `ReportLab` — PDF report generation for municipal submissions
- `Anthropic Claude API` — narrative generation: converts simulation statistics into plain-language assessment text for non-technical stakeholders

### IDE / Development Environment
- `infrared-skills` plugin loaded into Claude Code (CLAUDE.md + .claude-plugin/)
- 10 Jupyter cookbook notebooks as reference: `github.com/Infrared-city/infrared-skills`
- `.env` with `INFRARED_API_KEY` — loaded via `python-dotenv`

---

## 4. Business Model

**Archetype: B2G (Government) primary + Real Estate Fund B2B secondary**

Large contract sizes, longer sales cycles, milestone-based delivery. Fundamentally different financial shape from SiteScore — fewer deals, much higher ACV.

### Go-to-Market Entry Strategy

**Almaty entry point:**
1. Identify one district in the national renovation program pipeline
2. Offer a **free pilot RenovationMap** for that district
3. Generate a report showing the delta between current allocation and climate-optimized allocation (quantify wasted capex)
4. Use the report as the sales document for the full citywide contract

**Riyadh entry point:**
1. Target compound developers actively marketing to expats (English-speaking, data-literate buyers)
2. Show "outdoor usability hours" as a differentiator metric — translate UTCI maps to "days per year the pool deck is comfortable"
3. Upsell from SiteScore (new development) to RenovationMap (existing portfolio)

---

## 5. Revenue Streams

### Stream 1 — Municipal Government Contracts (B2G)

```
Single district climate triage (one-time):            $80,000  – $250,000
Citywide renovation sequencing model (Almaty):        $400,000 – $1,200,000
Annual monitoring contract (post-renovation delta):   $120,000 – $300,000 / year
```

Buyers: Almaty Akimat, KazSvyazService, Kazakhstan Ministry of Industry and Infrastructure Development. Saudi equivalents: REDF, National Housing Company, ROSHN.

### Stream 2 — Real Estate Fund Portfolio Audits (B2B)

```
Portfolio audit (20–50 assets, one-time):     $60,000  – $180,000
Annual portfolio re-score:                    $25,000  – $60,000 / year
Renovation scenario modeling (per scenario):  $8,000   – $25,000
```

Target funds in Almaty: Centras Capital, VISOR, Halyk Finance real estate division.
Target funds in Riyadh: Jadwa Investment, SICO, PIF-linked development entities.

### Stream 3 — Contractor Sales Tool Licensing (B2B)

Renovation contractors license RenovationMap to identify and pitch clients — arriving at an akimat meeting with a data-backed map of the 20 worst courtyards in the city wins tenders before they start.

```
Contractor sales tool license:        $500 – $1,200 / month per firm
Lead generation referral fee:         3–5% of contract value on closed deals
```

---

## 6. Unit Economics

```
CAC — government (relationship-driven):     $15,000 – $40,000
CAC — fund (direct sales):                  $3,000  – $8,000
Average blended contract value:             ~$180,000
LTV (3-year, annual renewal):               $380,000 – $600,000
Sales cycle:                                3–9 months (government) / 1–3 months (funds)
Gross margin:                               65% – 78%
Infrared API cost per district analysis:    €80 – €150 in credits
```

Gross margin is lower than SiteScore (65–78% vs. 90%+) due to services delivery component in government contracts, but ACV is 40x higher.

---

## 7. Revenue Projection

```
Year 1 — Pilot + first contracts
  1 municipal pilot (partial payment):       $80,000
  2 fund portfolio audits:                   $120,000
  Total:                                     ~$200,000

Year 2 — Market entry, both cities
  2 municipal contracts:                     $700,000
  3 fund audits + annual renewals:           $400,000
  Contractor licenses (10 firms):            $84,000
  Total:                                     ~$1,184,000

Year 3 — City replication (Dubai, Nur-Sultan, Abu Dhabi)
  4 cities, retainer contracts:              $2,400,000
  Fund portfolio platform (SaaS retainer):   $800,000
  Total:                                     ~$3,200,000
```

---

## 8. Strategic Moat

The defensible position is not the software — it is **owning the renovation prioritization methodology** that municipal programs reference. Once one city's official renovation program cites RenovationMap outputs in its allocation documentation, the switching cost is institutional, not technical.

Long-term: co-develop the scoring standard with a green building council or national standards body (KazSvyazService in Kazakhstan, Saudi Green Building Council in KSA). Make ClimateGrade a referenced metric in renovation fund disbursement criteria. At that point, every renovation project in scope requires a RenovationMap report — mandated, recurring, per-district revenue.

---

## 9. Relationship to Product A (SiteScore)

RenovationMap and SiteScore are financially and technically complementary:

| Dimension | SiteScore | RenovationMap |
|---|---|---|
| Asset lifecycle stage | Pre-development / new build | Existing stock / renovation |
| Buyer | Private developer, architect, investor | Government, fund, contractor |
| Revenue type | ARR subscriptions + per-report | Project contracts + retainers |
| Avg deal size | $2K – $20K | $80K – $1.2M |
| Sales cycle | Days – 4 weeks | 3 – 9 months |
| Gross margin | 82% – 94% | 65% – 78% |

SiteScore generates fast cash and validates the scoring model. RenovationMap generates large contracts and creates institutional data relationships. Data from RenovationMap interventions (what actually improves scores) trains and improves SiteScore models — a shared data flywheel that makes both products more accurate over time.

---

*Generated: 2026-05-28 | Context: Infrared.city SDK hackathon research — Almaty & Riyadh real estate focus*
