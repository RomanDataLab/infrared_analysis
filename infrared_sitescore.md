# Product A: SiteScore
### Microclimate Due Diligence for Real Estate Development

---

## 1. Product Description

**SiteScore** is a standardized microclimate assessment platform for real estate development sites and building proposals. It generates a **ClimateGrade (A–F)** for any polygon — development plot, proposed building massing, or existing property — by running physics-based environmental simulations via the Infrared.city SDK at ~1m resolution.

Positioned as the missing layer in property due diligence: today's reports cover soil, traffic, environmental contamination, structural condition. None cover microclimate quality — which directly determines energy bills, outdoor usability, tenant health, and future climate risk. SiteScore fills that gap.

### Primary Geographies
- **Almaty, Kazakhstan** — New residential and mixed-use development on city edges where mountain/valley wind patterns are unpredictable. Soviet-era infill projects where new towers shadow existing courtyards. Winter sun access is a critical quality-of-life and energy cost driver.
- **Riyadh, Saudi Arabia** — Vision 2030 construction boom generating hundreds of new compounds, mixed-use towers, and masterplan districts with essentially zero microclimate analysis at design stage. Outdoor usability of amenity zones (pools, terraces, pedestrian approaches) directly drives rental yield for compounds. Cooling costs are 50–70% of electricity bills.

### Core User Problem
A developer buys land or submits a masterplan with no quantified understanding of:
- How much winter sun the courtyard will receive (Almaty)
- How many hours per year the pool deck will be thermally usable (Riyadh)
- Whether the building orientation creates dangerous wind corridors
- How much the proposed tower degrades microclimate for neighboring properties

SiteScore answers all of this before groundbreaking — when design changes are cheap.

### What It Produces
- **ClimateGrade (A–F)** — composite score with four sub-scores (see below)
- **Heatmap overlays** — UTCI, wind speed, solar irradiance, sky view factor at 1m resolution
- **Before/after massing comparison** — baseline vs. proposed geometry, delta heatmaps
- **Parametric design feedback** — rotate building 15°, add courtyard, change gap between towers → instant re-score
- **ClimateGrade Certificate** — branded PDF for use in planning submissions, marketing materials, bank underwriting packages

### The Four Sub-Scores

| Sub-Score | Almaty Priority | Riyadh Priority |
|---|---|---|
| **Winter Sun Access** | HIGH — hours of direct sun in Dec on courtyard/facade | LOW |
| **Summer Heat Stress** | MEDIUM | HIGH — UTCI dangerous hours in outdoor amenity zones |
| **Wind Exposure** | HIGH — cold wind tunneling between buildings | MEDIUM — Shamal sandstorm exposure index |
| **Outdoor Usability** | Hours/year outdoor space is thermally comfortable | Hours/year pool deck / terrace is usable |

Weights are climate-context-aware: Almaty profile emphasizes winter sun + wind; Riyadh profile emphasizes summer UTCI + usability hours.

---

## 2. Target Customers

| Segment | Geography | Buyer Title | Use Case |
|---|---|---|---|
| Real estate developer | Both | Project director, land acquisition manager | Pre-acquisition due diligence, permit submission |
| Architecture / planning studio | Both | Principal architect, urban designer | Design optimization, client reporting |
| Real estate investor / fund | Both | Asset manager, acquisition analyst | Portfolio screening, underwriting |
| Bank / mortgage lender | Both | Credit risk, real estate finance | Climate risk in loan underwriting |
| City planning department | Both | Chief planner, permit officer | Development approval workflow |

---

## 3. Technical Architecture

### Core Analysis Engine
- **Infrared.city Python SDK** — primary simulation engine
  - `wind-speed` — pedestrian-level wind magnitude, 8-direction sweep
  - `pedestrian-wind-comfort` — Lawson / VDI / Davenport classification
  - `direct-sun-hours` — winter and summer solar access per surface
  - `solar-radiation` — cumulative kWh/m² on rooftops and facades
  - `sky-view-factors` — sky hemisphere visibility (0–100%)
  - `thermal-comfort-index` — UTCI outdoor stress map
  - `thermal-comfort-statistics` — % time in heat/cold stress annually
  - `daylight-availability` — ground-level daylight distribution
- `run_area_and_wait()` for synchronous single-site reports
- `run_area()` + webhook for async batch (parameter sweeps, massing variants)
- `preview_area_cost()` — always run before submission to control credit spend
- Directional argmax + smart-blend merge for multi-tile wind analyses

### Geometry Input Pipeline
- **Baseline geometry**: `osmnx` — pull existing building footprints + heights from OpenStreetMap
- **Proposed massing**: GeoJSON drawn on Mapbox web UI (draw tool) or uploaded as file
- `shapely` — polygon validation, buffering, context zone construction
- `geopandas` — spatial joins, coordinate handling
- `pyproj` — WGS84 reprojection before SDK submission
- `py-dotbim` — parse 3D building geometry returned by SDK Buildings API
- `trimesh` — mesh volume, floor area ratio, shadow casting pre-checks

### Weather & Environmental Data
- `overpy` (OSM Overpass) — tree locations and ground surface types fed to SDK
- OpenWeatherMap / Visual Crossing — hourly weather for `TimePeriod` analysis windows
- ERA5 (Copernicus) — multi-year climate reanalysis for robust UTCI statistics
- Mapbox surface layer — asphalt, concrete, vegetation, water, soil classification

### Raster Processing
- `numpy` — native SDK output (2D masked arrays per analysis)
- `rasterio` — georeference outputs, export GeoTIFF, reproject to local CRS
- `xarray` — multi-analysis composite: stack wind × 8 directions, UTCI × 12 months
- `scipy.ndimage` — spatial smoothing, percentile statistics per zone
- `scikit-image` — segment comfort/stress zones for scoring

### Scoring Model
```python
# ClimateGrade composite (simplified)
sub_scores = {
    "winter_sun":      normalize(direct_sun_hours_dec, city_profile),
    "heat_stress":     normalize(1 - utci_danger_pct, city_profile),
    "wind_exposure":   normalize(1 - wind_discomfort_pct, city_profile),
    "outdoor_usability": normalize(comfortable_hours_pct, city_profile)
}
weighted_score = sum(w[k] * sub_scores[k] for k in sub_scores)
grade = score_to_grade(weighted_score)  # A=90-100, B=75-89, C=60-74, D=45-59, F<45
```
- `scikit-learn` — regression model trained on intervention outcomes (from RenovationMap data flywheel)
- City profile weights configurable per climate context (Almaty vs. Riyadh vs. future cities)

### Backend
- `FastAPI` — REST API: POST polygon + optional massing GeoJSON → async job → GET ClimateGrade
- `Celery` + `Redis` — job queue (SDK analyses run 30–120s; don't block HTTP)
- `PostgreSQL` + `PostGIS` — spatial result storage, parcel ID linkage, historical grade tracking
- `SQLAlchemy` — ORM
- `boto3` / S3 — presigned storage for large SDK payloads (BigPayloadError handler)
- `pydantic` — request/response validation (consistent with SDK internals)
- Webhook endpoint for Infrared.city async callbacks with HMAC signature verification

### Visualization
- `pydeck` / `deck.gl` — interactive heatmap overlays on real city basemap
- `Mapbox GL JS` — web map with satellite imagery, draw polygon tool for site input
- `plotly` — before/after comparison charts, sub-score radar chart
- `WeasyPrint` — PDF certificate generation (ClimateGrade report)
- `Anthropic Claude API` — plain-language narrative: converts simulation stats into readable assessment text for non-technical stakeholders (developers, investors, permit officers)

### Frontend
- `Next.js` / `React` — web application
- `Maplibre GL JS` — open-source Mapbox alternative for map rendering
- `Streamlit` — rapid hackathon prototype / internal tool version
- Draw tool: `@mapbox/mapbox-gl-draw` — polygon input for site boundaries

### IDE / Development
- `infrared-skills` plugin in Claude Code (CLAUDE.md + .claude-plugin/)
- Cookbook reference: `github.com/Infrared-city/infrared-skills/cookbook/notebooks/`
- `.env` → `INFRARED_API_KEY` via `python-dotenv`
- Cost preview before every SDK run to manage credit spend

---

## 4. Business Model

**Archetype: B2B SaaS + Report-as-a-Service + Certification Standard**

Three revenue streams stacked by product maturity, building from transactional to recurring to institutional.

### Go-to-Market Entry Strategy

**Almaty entry:**
1. Partner with 2–3 architecture studios already working on residential developments
2. Offer free first report — let architects see the output, share with their developer client
3. Convert architect to monthly subscription; developer to per-report buyer
4. Use first ClimateGrade-certified project as PR case study

**Riyadh entry:**
1. Target compound developers marketing to expats — they compete on outdoor lifestyle
2. Lead with "outdoor usability hours" metric — directly maps to rental yield story
3. Offer free benchmark: "see how your existing compound scores vs. competitors"
4. Upsell to full certification for use in CBRE/JLL valuation reports

---

## 5. Revenue Streams

### Stream 1 — Per-Report (Year 1, immediate revenue)

Positioned as a due diligence line item — same budget category as geotechnical surveys or traffic impact assessments.

```
Small residential plot, Almaty (< 5,000 m²):        $2,000  – $5,000  per report
Medium mixed-use development:                        $5,000  – $12,000 per report
Large compound / masterplan, Riyadh (> 20,000 m²):  $12,000 – $30,000 per report
Enterprise / custom analysis:                        $30,000 – $80,000 per report
```

### Stream 2 — Platform Subscription (Year 1–2, recurring ARR base)

Architects and in-house design teams run analyses continuously and need a subscription, not per-report billing.

```
Architecture studio (1–5 users):          $400  – $800  / month
Developer in-house design team:           $1,200 – $2,500 / month
Real estate fund (API access):            $5,000 – $15,000 / month
```

Target: 50–100 studios in Almaty + Riyadh by end of Year 1 = **$500K – $1.5M ARR**

### Stream 3 — ClimateGrade Certification (Year 2–3, defensible moat)

Once ClimateGrade is co-developed with a real estate association or green building council as a recognized label, developers pay for the **certified stamp** — used in marketing, planning submissions, and bank underwriting.

```
ClimateGrade Certification (per building):    $3,000  – $12,000
Annual recertification (conditions change):   $800    – $2,000  / year
Bank / insurer data API feed:                 $50,000 – $200,000 / year (enterprise)
```

This is the LEED model — but 90% cheaper because it is automated simulation, not manual auditing.

---

## 6. Unit Economics

```
CAC — direct sales to developers:          $800   – $2,000
CAC — inbound via architects:              $150   – $400
Average blended contract value, Year 1:    ~$4,500
LTV (3-year, 70% retention):               $9,000 – $18,000
LTV:CAC ratio:                             8:1 – 15:1   (strong SaaS profile)
Gross margin:                              82% – 94%
Infrared API cost per report:              €2 – €30 in credits (depending on polygon size)
```

Margin is high because the Infrared.city API cost is a small fraction of the charge. The value is in the scoring methodology, the UI, and — eventually — the certified brand recognition.

### Value Created vs. Cost of Analysis

| Scenario | Value at stake | Analysis cost | Ratio |
|---|---|---|---|
| Riyadh compound — Grade A vs C on $80M asset | +15% yield = **$12M** asset value delta | $12,000 | **1,000x** |
| Almaty developer — optimal orientation saves 8% heating cost over 30 years | **$400K** NPV savings | $4,000 | **100x** |
| Bank underwriting $50M loan — no climate risk data | Potential NPL exposure | $5,000 | Incalculable |

---

## 7. Revenue Projection

```
Year 1 — Hackathon → pilot clients
  20 reports:                              $90,000
  15 studio subscriptions:                 $54,000
  Total:                                   ~$144,000

Year 2 — Market entry, both cities
  180 reports:                             $540,000
  60 subscriptions (studios + funds):      $576,000
  First certifications (10 buildings):     $60,000
  Total:                                   ~$1,176,000

Year 3 — Certification standard + expansion
  Reports + subscriptions:                 $1,400,000
  Certification program (50+ buildings):   $400,000
  Bank / insurer API deals (3 clients):    $600,000
  Total:                                   ~$2,400,000
```

---

## 8. Strategic Moat

The moat is **not the software** — it is owning the ClimateGrade scoring standard.

Path to defensibility:
1. Co-develop the grading methodology with Kazakhstan Green Building Council or Saudi Green Building Council
2. Get first voluntary references in planning guidance documents
3. Push for inclusion in national green building codes (Saudi Vision 2030 green building standards are actively being revised)
4. At mandate stage: every new development application in scope requires a ClimateGrade report — recurring, per-building, non-discretionary revenue

Analogues: EPC (Energy Performance Certificate) in the EU — mandatory since 2008, assessors charge £50–500 per certificate on millions of transactions per year. SiteScore automates this at 10x the accuracy and 1/10th the cost of manual assessment.

---

## 9. Relationship to Product B (RenovationMap)

| Dimension | SiteScore | RenovationMap |
|---|---|---|
| Asset lifecycle | Pre-development / new build | Existing stock / renovation |
| Buyer | Developer, architect, investor | Government, fund, contractor |
| Revenue type | ARR subscriptions + per-report | Project contracts + retainers |
| Avg deal size | $2K – $20K | $80K – $1.2M |
| Sales cycle | Days – 4 weeks | 3 – 9 months |
| Gross margin | 82% – 94% | 65% – 78% |

**Data flywheel:** RenovationMap tracks which physical interventions actually improve ClimateGrade scores post-renovation. That ground-truth data trains SiteScore's scoring model to become more predictive over time — a compounding accuracy advantage that pure SiteScore competitors cannot replicate.

**Pipeline logic:** SiteScore lands the relationship with a developer at project inception. As that developer accumulates assets, they need RenovationMap for portfolio triage. One SDK, one platform, full asset lifecycle coverage.

---

## 10. Hackathon Demo Scope (5 Days)

```
Day 1:  SDK integration, run baseline analyses on 1 Almaty site + 1 Riyadh site
Day 2:  Build scoring model — normalize 4 sub-scores, assign A–F grade
Day 3:  Build intervention simulator — swap massing GeoJSON → re-run → delta score
Day 4:  Frontend — Mapbox draw tool, pydeck heatmap overlay, grade card UI
Day 5:  ClimateGrade PDF certificate, polish demo, pitch narrative
```

**Minimum demo**: two real sites (Almaty mikrorayon courtyard + Riyadh compound), two before/after massing scenarios, one grade card output, one PDF certificate. Complete proof of concept in 5 days.

**Pitch hook:** *"Every city built for cars has a routing engine. No city built for extreme climate has a microclimate due diligence standard — until now."*

---

*Generated: 2026-05-28 | Context: Infrared.city SDK hackathon research — Almaty & Riyadh real estate focus*
