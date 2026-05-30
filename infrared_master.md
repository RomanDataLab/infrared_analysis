# ClimateGrade — Master Pitch & Architecture Document
### Microclimate Intelligence for Extreme-Climate Real Estate
#### Almaty × Riyadh × Mecca × Astana | Powered by Infrared.city SDK

---

## PITCH DECK OUTLINE

---

### Slide 1 — Cover

**ClimateGrade**
*The missing due diligence layer for real estate in extreme climates*

Almaty · Riyadh · [Next City]
Hackathon Demo Build — 2026

---

### Slide 2 — The Problem

> Real estate in extreme-climate cities is priced, built, and renovated with zero quantified understanding of microclimate quality.

**In Almaty:**
- Soviet mikrorayon courtyards are wind tunnels at -25°C
- New towers shadow neighboring buildings — residents lose 3–4 hours of winter sun per day
- National renovation program spends $500M+/year with no spatial priority logic — wrong buildings get fixed first

**In Riyadh:**
- Compound pool decks are unusable 6 months/year — but no developer measures this
- New $80M compounds are designed with zero outdoor thermal analysis
- Cooling costs hit 70% of electricity bills — building orientation is never optimized

**The gap:** Soil surveys exist. Traffic studies exist. Environmental impact assessments exist.
**Microclimate due diligence does not exist. Anywhere.**

---

### Slide 3 — The Insight

Every $1 spent on microclimate analysis at design stage prevents $100–$1,000 in stranded value post-construction.

| Situation | Value at stake | Cost of knowing | Ratio |
|---|---|---|---|
| Riyadh compound Grade A vs C on $80M asset | $12M yield delta | $12,000 report | **1,000x** |
| Almaty developer optimal orientation → 8% heating savings | $400K NPV | $4,000 report | **100x** |
| Bank underwriting $50M loan, no climate risk data | Potential NPL | $5,000 | ∞ |

**The data layer exists.** Physics-based urban simulation at 1m resolution is available today via API.
**The product packaging does not.** We build it.

---

### Slide 4 — The Solution

**ClimateGrade** — a standardized microclimate score for any real estate asset or development site.

```
Input:  Any polygon (development plot, building proposal, existing property)
Engine: Infrared.city SDK — physics-based CFD + thermal simulation at ~1m resolution
Output: ClimateGrade (A–F) + heatmap overlays + plain-language report
```

Four sub-scores, climate-context-weighted:

| Sub-Score | Almaty weight | Riyadh weight |
|---|---|---|
| Winter Sun Access | ████████ HIGH | ██ LOW |
| Summer Heat Stress | ████ MED | ████████ HIGH |
| Wind Exposure | ████████ HIGH | ████ MED |
| Outdoor Usability | ████ MED | ████████ HIGH |

**One platform. Two products. Full asset lifecycle.**

---

### Slide 5 — Product A: SiteScore

**For new development and acquisitions**

- Draw site polygon on map → submit proposed massing → get ClimateGrade in minutes
- Before/after comparison: rotate building 15° → see wind impact instantly
- ClimateGrade Certificate: PDF for planning submissions, bank packages, marketing
- Sold to: developers, architects, investors, banks

```
Entry price:    $2,000 – $5,000 per report (small site)
Subscription:   $400 – $2,500/month (architecture studios, design teams)
Certification:  $3,000 – $12,000 per building (planning/marketing use)
Margin:         82% – 94%
```

*Think: EPC (Energy Performance Certificate) — but automated, at 1m resolution, for outdoor microclimate.*

---

### Slide 6 — Product B: RenovationMap

**For existing stock and municipal renovation programs**

- Input district polygon → batch-analyze all courtyards and open spaces
- Output: ranked intervention map — worst wind tunnels, mutual shadowing buildings, cold spots
- Scenario modeling: add tree row → delta UTCI improvement; change surface → thermal gain
- Ranks interventions by comfort-gain per $1,000 spent
- Sold to: municipal governments, real estate funds, renovation contractors

```
District triage (one-time):     $80,000 – $250,000
Citywide contract:              $400,000 – $1,200,000
Annual monitoring retainer:     $120,000 – $300,000/year
Margin:                         65% – 78%
```

*Think: turning Kazakhstan's $500M/year renovation program from politically-driven to data-driven.*

---

### Slide 7 — Market Opportunity

**Beachhead: Almaty + Riyadh**

| Market | Annual construction value | Renovation program | Key driver |
|---|---|---|---|
| Kazakhstan | ~$8B/year | $500M+/year national program | Mikrorayon stock, energy reform |
| Saudi Arabia | ~$60B/year (Vision 2030) | Compound retrofits | Outdoor livability, cooling costs |

**Expansion path (Year 2–3):**
Dubai → Abu Dhabi → Nur-Sultan → Tashkent → Tbilisi → any city where climate is a real estate variable

**The TAM framing:**
Global green building certification market: **$50B+/year**
ClimateGrade addresses the one analysis type none of them automate: outdoor microclimate.

---

### Slide 8 — Business Model Summary

```
                    SiteScore                    RenovationMap
Archetype:          B2B SaaS + per-report        B2G + institutional B2B
Buyer:              Developer / architect /       Government / fund /
                    investor                      contractor
Revenue type:       Subscriptions + reports +     Project contracts +
                    certifications                retainers
Avg deal size:      $2K – $20K                   $80K – $1.2M
Sales cycle:        Days – 4 weeks               3 – 9 months
Gross margin:       82% – 94%                    65% – 78%
CAC:                $150 – $2,000                $3,000 – $40,000
LTV:CAC:            8:1 – 15:1                   9:1 – 15:1
```

**Combined revenue forecast:**

```
Year 1:   $175K – $350K     (pilots, first subscriptions, 1 municipal contract)
Year 2:   $1.5M – $2.4M    (both cities live, certification launched)
Year 3:   $5M – $8M        (3–4 city expansion, bank API deals, mandate traction)
```

---

### Slide 9 — The Strategic Moat

**Short term:** First mover with physics-based scoring in these markets.

**Medium term:** Proprietary dataset — every analysis run teaches the model which interventions actually move grades. Competitors starting from scratch cannot replicate this.

**Long term:** Become the regulatory standard.
- Co-develop grading methodology with Kazakhstan Green Building Council / Saudi Green Building Council
- Get voluntary references in planning guidance
- Push for inclusion in national green building codes
- At mandate: every new development requires a ClimateGrade report

**The EPC analogue:** EU mandated Energy Performance Certificates in 2008.
Today: millions of certificates issued per year across Europe at €50–500 each.
ClimateGrade is that — for outdoor microclimate — in the fastest-growing construction markets in the world.

---

### Slide 10 — Hackathon Demo

**What we build in 5 days:**

```
Day 1:  SDK setup + baseline analyses on 1 Almaty site + 1 Riyadh site
Day 2:  Scoring model — normalize 4 sub-scores, grade algorithm, city profiles
Day 3:  Intervention simulator — swap GeoJSON massing → re-run → delta heatmap
Day 4:  Web frontend — Mapbox draw tool + pydeck heatmap + grade card UI
Day 5:  PDF certificate, polish demo, pitch narrative
```

**Demo story:**
1. Open map → draw polygon around a real Almaty mikrorayon courtyard → ClimateGrade F (wind tunnel, no winter sun)
2. Propose intervention: add windbreak tree row + resurface courtyard → re-run → ClimateGrade C
3. Switch to Riyadh → draw compound boundary → Grade D (pool deck unusable 7 months/year)
4. Propose shade canopy + reorient amenity zone → Grade B → "$2.4M annual rental yield improvement on this asset"

**One sentence:** *"We just told you more about that property's climate quality than any due diligence report ever written for it."*

---
---

## TECHNICAL ARCHITECTURE

---

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ClimateGrade Platform                        │
├─────────────────┬───────────────────────────────┬───────────────────┤
│   FRONTEND      │         BACKEND API            │  ANALYSIS ENGINE  │
│                 │                                │                   │
│  Next.js/React  │        FastAPI                 │  Infrared.city    │
│  Maplibre GL    │        ┌──────────────┐        │  Python SDK       │
│  pydeck         │        │ Celery Queue │        │                   │
│  Draw polygon   │◄──────►│ Redis broker │◄──────►│  - wind-speed     │
│  Heatmap layer  │        └──────────────┘        │  - utci           │
│  Grade card UI  │        PostGIS DB              │  - solar-radiation│
│  PDF cert view  │        S3 result store         │  - sky-view       │
│                 │        Claude API (narrative)   │  - daylight       │
└─────────────────┴───────────────────────────────┴───────────────────┘
```

---

### Data Flow: SiteScore (New Development)

```
User draws polygon on Mapbox
         │
         ▼
POST /analyze  {polygon: GeoJSON, massing: GeoJSON (optional), city_profile: "almaty"|"riyadh"}
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI                                            │
│  1. Validate polygon (pydantic + shapely)           │
│  2. Fetch OSM buildings (osmnx) for context         │
│  3. Merge proposed massing if provided              │
│  4. Enqueue analysis job (Celery)                   │
│  5. Return job_id                                   │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Celery Worker                                      │
│  1. preview_area_cost() → check credits             │
│  2. run_area_and_wait([                             │
│       WindModelRequest(8 directions),               │
│       ThermalComfortRequest(summer + winter),       │
│       DirectSunHoursRequest(dec + jun),             │
│       SkyViewFactorsRequest()                       │
│     ], polygon, buildings=osm_buildings)            │
│  3. Merge wind results (directional_blend)          │
│  4. Stack UTCI arrays (xarray)                      │
│  5. Compute 4 sub-scores (numpy + scikit-learn)     │
│  6. Assign ClimateGrade A–F                         │
│  7. Store GeoTIFF results (rasterio → S3)           │
│  8. Store grade record (PostGIS)                    │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Claude API (narrative generation)                  │
│  Input: sub-scores + percentile stats + city        │
│  Output: plain-language assessment paragraph        │
│  "This site receives 2.1 hours of direct sun        │
│   in December — 40% below Almaty median for         │
│   residential courtyards. Wind exposure peaks       │
│   at 8.3 m/s from NW, creating dangerous           │
│   pedestrian conditions Oct–Mar..."                 │
└─────────────────────────────────────────────────────┘
         │
         ▼
GET /result/{job_id}
→ {grade: "C", sub_scores: {...}, heatmap_url: "...", narrative: "...", certificate_url: "..."}
```

---

### Data Flow: RenovationMap (Existing District)

```
User uploads district polygon (GeoJSON or KML)
         │
         ▼
POST /district/analyze  {polygon: GeoJSON, city: "almaty"|"riyadh", season: "winter"|"summer"|"annual"}
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI                                            │
│  1. Auto-tile district into analysis cells          │
│     (512m × 512m tiles with 50% overlap)           │
│  2. Extract courtyard polygons from OSM buildings   │
│  3. Enqueue batch job (Celery group)                │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Celery Workers (parallel, 20-thread pool)          │
│  Per tile:                                          │
│  1. run_area([UTCI, wind, direct_sun], tile_polygon)│
│  2. Return numpy arrays per tile                    │
│                                                     │
│  Post-merge:                                        │
│  1. Stitch tile results (rasterio mosaic)           │
│  2. xarray: stack 12-month UTCI into annual stats   │
│  3. Compute SeverityScore per courtyard cell:       │
│     S = w1·UTCI_stress% + w2·wind_discomfort%       │
│         + w3·(1 - winter_sun_normalized)            │
│  4. Rank all courtyards by SeverityScore            │
│  5. Run intervention scenarios for top-20 worst:    │
│     - Add tree row → delta S                        │
│     - Change surface material → delta S             │
│     - Infill building gap → delta S (wind vs. sun)  │
│  6. Sort interventions by delta_S / estimated_cost  │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Output                                             │
│  - District severity heatmap (GeoTIFF → pydeck)     │
│  - Ranked courtyard list (PostGIS → JSON)           │
│  - Intervention priority map (GeoJSON overlay)      │
│  - PDF report (WeasyPrint) with:                    │
│    · Executive summary (Claude API narrative)       │
│    · Top 10 intervention recommendations            │
│    · Estimated comfort gain per ₸/SAR spent         │
│    · Before/after simulation renders                │
└─────────────────────────────────────────────────────┘
```

---

### Scoring Model Detail

```python
# City profile weights
CITY_PROFILES = {
    "almaty": {
        "winter_sun":       0.35,   # Critical — mental health, heating costs
        "wind_exposure":    0.35,   # Buran + cold wind tunneling
        "heat_stress":      0.15,   # Short hot summers
        "outdoor_usability":0.15
    },
    "riyadh": {
        "winter_sun":       0.05,   # Mild winters, sun not a concern
        "wind_exposure":    0.20,   # Shamal sandstorms
        "heat_stress":      0.40,   # Dominant concern
        "outdoor_usability":0.35    # Direct yield impact
    }
}

# Sub-score normalization (0–100)
def score_winter_sun(direct_sun_dec_hours, city):
    # Almaty benchmark: 3.5h/day median for residential courtyards
    benchmarks = {"almaty": 3.5, "riyadh": 6.0}
    return min(100, (direct_sun_dec_hours / benchmarks[city]) * 100)

def score_heat_stress(utci_stats):
    # % of occupied hours NOT in heat stress (UTCI > 38°C)
    danger_pct = utci_stats.pct_strong_heat_stress + utci_stats.pct_very_strong_heat_stress
    return max(0, 100 - danger_pct * 2)

def score_wind(pwc_stats):
    # % of hours with acceptable pedestrian wind comfort (Lawson A/B)
    acceptable_pct = pwc_stats.pct_sitting + pwc_stats.pct_standing + pwc_stats.pct_walking
    return min(100, acceptable_pct)

def score_usability(utci_stats, city):
    # Hours/year where UTCI is in "comfortable" or "slight stress" range
    comfortable_hours = utci_stats.hours_no_stress + utci_stats.hours_slight_cold_stress
    annual_hours = 8760
    return min(100, (comfortable_hours / annual_hours) * 100)

def climate_grade(polygon_geojson, city="almaty"):
    weights = CITY_PROFILES[city]
    composite = (
        weights["winter_sun"]        * score_winter_sun(...)   +
        weights["heat_stress"]       * score_heat_stress(...)  +
        weights["wind_exposure"]     * score_wind(...)         +
        weights["outdoor_usability"] * score_usability(...)
    )
    thresholds = {90: "A", 75: "B", 60: "C", 45: "D", 0: "F"}
    return next(g for floor, g in sorted(thresholds.items(), reverse=True)
                if composite >= floor)
```

---

### Full Tech Stack Reference

```
Layer               Tool                        Purpose
─────────────────────────────────────────────────────────────────────
SIMULATION ENGINE
                    infrared-sdk                Core analysis API
                    python-dotenv               API key management
                    pydantic                    Payload validation

GEOMETRY INPUT
                    osmnx                       OSM building footprints + street networks
                    geopandas                   GeoJSON handling, spatial joins
                    shapely                     Polygon construction, validation
                    pyproj                      WGS84 coordinate transformation
                    py-dotbim                   DotBim 3D building format parser
                    trimesh                     Mesh volume, shadow pre-checks
                    overpy                      OSM Overpass (trees, ground surfaces)

WEATHER DATA
                    openweathermap API          Hourly weather for TimePeriod windows
                    ERA5 / Copernicus           Multi-year climate reanalysis
                    Visual Crossing             Backup weather source

RASTER PROCESSING
                    numpy                       Native SDK array format
                    rasterio                    Georeference, GeoTIFF export, mosaic
                    xarray                      Multi-analysis stacking (time × space)
                    scipy.ndimage               Spatial smoothing, zone statistics
                    scikit-image                Comfort zone segmentation

SCORING / ML
                    scikit-learn                Grade regression model
                    lightgbm                    Yield-vs-microclimate predictive model
                    pandas                      Tabular result processing

BACKEND
                    fastapi                     REST API layer
                    celery                      Async job queue
                    redis                       Celery broker + result backend
                    postgresql + postgis        Spatial result storage, parcel linking
                    sqlalchemy                  ORM
                    boto3                       S3 for large payload storage

AI NARRATIVE
                    anthropic (Claude API)      Plain-language report generation
                    prompt caching              Cost optimization on repeated contexts

VISUALIZATION
                    pydeck / deck.gl            Interactive heatmap (primary)
                    maplibre-gl-js              Web map base layer
                    mapbox-gl-draw              Polygon draw tool (site input)
                    plotly                      Charts, radar sub-score display
                    matplotlib                  Static analysis figures

FRONTEND
                    next.js / react             Web application
                    streamlit                   Rapid hackathon prototype

REPORTING
                    weasyprint                  PDF certificate generation
                    reportlab                   Backup PDF engine

DEV ENVIRONMENT
                    infrared-skills plugin      Claude Code plugin (CLAUDE.md)
                    jupyter                     SDK exploration, notebook prototyping
                    docker                      Containerized deployment
                    github actions              CI/CD
```

---

### Infrastructure Diagram

```
                        ┌──────────────┐
                        │   User (web) │
                        └──────┬───────┘
                               │ HTTPS
                        ┌──────▼───────┐
                        │  Next.js     │
                        │  Frontend    │
                        │  Maplibre    │
                        │  pydeck      │
                        └──────┬───────┘
                               │ REST API
                        ┌──────▼───────────────────┐
                        │      FastAPI              │
                        │  /analyze (SiteScore)     │
                        │  /district (RenovationMap)│
                        │  /result/{job_id}         │
                        │  /certificate/{id}        │
                        └──┬──────────┬─────────────┘
                           │          │
               ┌───────────▼──┐  ┌───▼──────────────┐
               │    Redis     │  │   PostgreSQL +    │
               │  Job Queue   │  │   PostGIS         │
               └───────┬──────┘  └───────────────────┘
                       │
          ┌────────────▼─────────────┐
          │      Celery Workers       │
          │   (20-thread pool)        │
          │                           │
          │  osmnx → fetch buildings  │
          │  SDK → run analyses       │
          │  rasterio → process grid  │
          │  scikit-learn → grade     │
          │  Claude API → narrative   │
          │  WeasyPrint → PDF cert    │
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐      ┌─────────────────┐
          │   Infrared.city SDK      │      │      AWS S3      │
          │   (External API)         │      │  Result storage  │
          │                          │      │  GeoTIFF files   │
          │  Wind × 8 directions     │      │  PDF certs       │
          │  UTCI × 12 months        │      └─────────────────┘
          │  Solar + sky view        │
          │  Buildings + vegetation  │
          └──────────────────────────┘
```

---

### API Endpoints Reference

```
POST   /analyze
       Body: {polygon, massing?, city_profile, analyses?}
       Returns: {job_id, estimated_cost_tokens, eta_seconds}

GET    /result/{job_id}
       Returns: {status, grade, sub_scores, heatmap_urls, narrative, certificate_url}

POST   /district/analyze
       Body: {polygon, city, season, intervention_budget?}
       Returns: {job_id, tile_count, eta_seconds}

GET    /district/{job_id}
       Returns: {status, severity_map_url, ranked_courtyards[], interventions[]}

GET    /certificate/{job_id}
       Returns: PDF stream (ClimateGrade certificate)

POST   /compare
       Body: {baseline_polygon, alternative_polygon, city_profile}
       Returns: {baseline_grade, alternative_grade, delta_heatmap_url}

GET    /preview-cost
       Body: {polygon, analyses[]}
       Returns: {estimated_cost_tokens, estimated_cost_eur}
```

---

### Webhook Handler (Infrared.city async callback)

```python
@app.post("/webhook/infrared")
async def infrared_webhook(request: Request):
    # 1. Verify HMAC signature (raw bytes — do NOT re-encode)
    signature = request.headers.get("X-Infrared-Signature")
    body = await request.body()
    verify_signature(body, signature, INFRARED_WEBHOOK_SECRET)

    # 2. Parse job completion event
    event = InfraredWebhookEvent.model_validate_json(body)

    # 3. Fetch merged result grid
    result = await client.merge_area_jobs(
        event.job_ids,
        strategy="directional_blend",
        wind_direction_deg=event.wind_direction
    )

    # 4. Continue scoring pipeline
    await score_and_store(event.analysis_id, result)
```

---

### Cost Management

```python
# Always preview before running — never burn credits blindly
async def safe_run(client, requests, polygon, threshold_tokens=500):
    preview = client.preview_area_cost(requests, polygon)
    if preview.estimated_cost_tokens > threshold_tokens:
        raise CostThresholdExceeded(
            f"Estimated {preview.estimated_cost_tokens} tokens — above limit {threshold_tokens}"
        )
    return await client.run_area_and_wait(requests, polygon)
```

**Credit budget per product tier:**

```
Infrared Personal (€50/mo, 1,000 credits):
  → ~50–200 SiteScore reports/month depending on polygon size
  → Hackathon: fully covers demo development

Infrared Team (€250/mo, 5,000 credits):
  → ~250–500 SiteScore reports or 5–10 district RenovationMaps
  → Early commercial stage

Infrared Pro (€500/mo, 10,000 credits):
  → Pass-through pricing: €2–30 COGS per report vs. $2,000–30,000 charged
  → Gross margin maintained at 82–94% even at this plan
```

---

## ROADMAP

```
PHASE 1 — Hackathon (Week 1)
  ✓ SDK integration + scoring model
  ✓ 2 demo sites (Almaty + Riyadh)
  ✓ ClimateGrade output + PDF certificate
  ✓ Pitch deck delivered

PHASE 2 — Pilot (Month 1–3)
  → Free SiteScore reports for 5 Almaty architecture studios
  → Free RenovationMap pilot for 1 Almaty district (akimat intro)
  → First paying customers (target: 3 developer reports)
  → Riyadh: cold outreach to 3 compound developers

PHASE 3 — Commercial Launch (Month 3–9)
  → SiteScore subscription tier live
  → RenovationMap first paid municipal contract
  → ClimateGrade methodology published (white paper)
  → Integration with CBRE/JLL valuation workflows (conversations)

PHASE 4 — Standard Setting (Month 9–18)
  → Co-develop grading standard with Kazakhstan Green Building Council
  → Saudi Green Building Council engagement
  → Bank/insurer API pilot (1 lender in each market)
  → Series A fundraise with $1.5M ARR traction

PHASE 5 — Mandate Path (Year 2–3)
  → Push for voluntary ClimateGrade reference in planning guidance
  → Expand: Dubai, Abu Dhabi, Nur-Sultan, Tashkent
  → 3–4 city active contracts, $5M+ ARR
  → Regulatory mandate in first city = inflection point
```

---

*Generated: 2026-05-28 | ClimateGrade — Infrared.city SDK Hackathon Build*
*Products: SiteScore (infrared_sitescore.md) + RenovationMap (infrared_pro.md)*

---

## CANDIDATE RENOVATION ASSETS

Four high-value sites selected for RenovationMap demo and commercial pipeline.
Pricing sourced: Numbeo (May 2026), krisha.kz, aqar.fm.
Exchange rates: 1 SAR = $0.267 USD · 1 KZT = $0.0021 USD

---

### Asset 1 — Al-Aziziyah Residential District | Mecca, Saudi Arabia

```
Centerpoint:      21.4166°N,  39.8551°E
SDK coordinates:  [39.8551, 21.4166]   ← GeoJSON [lng, lat]
Distance to Haram: ~2.7 km
Building stock:   Government iskan (1970s–1990s), 5–9 story blocks
Scale:            ~500,000 residents + pilgrim overflow
```

| Metric | Value |
|---|---|
| Current price/m² | SAR 8,500–12,000 · **$2,270–$3,200** |
| Post-renovation price/m² | SAR 15,000–22,000 · **$4,000–$5,870** |
| Value uplift | **+70–83%** |
| ClimateGrade (est.) | **F** |

**Climate issues:** Valley bowl traps extreme heat (UTCI >45°C outdoors in summer). Barren concrete courtyards, zero tree cover, no shading infrastructure. Wind from surrounding mountains creates unpredictable thermal corridors between blocks.

**Renovation thesis:** Vision 2030 iskan upgrade program + Umrah economy repositioning. Improved outdoor comfort → serviced apartment conversion → 3–4x rental yield uplift vs. current residential use.

```python
al_aziziyah_polygon = {
    "type": "Polygon",
    "coordinates": [[
        [39.8451, 21.4086],
        [39.8651, 21.4086],
        [39.8651, 21.4246],
        [39.8451, 21.4246],
        [39.8451, 21.4086]
    ]]
}
```

---

### Asset 2 — Jarwal Neighborhood | Mecca, Saudi Arabia

```
Centerpoint:      21.4278°N,  39.8142°E
SDK coordinates:  [39.8142, 21.4278]   ← GeoJSON [lng, lat]
Distance to Haram: ~0.8 km
Building stock:   Dense pre-1970s to 1990s residential/commercial, 5–8 stories
Scale:            One of the oldest surviving residential zones near the Haram
```

| Metric | Value |
|---|---|
| Current price/m² | SAR 18,600–26,000 · **$4,965–$6,940** |
| Post-renovation price/m² | SAR 26,000–35,000 · **$6,940–$9,350** |
| Value uplift | **+35–40%** |
| ClimateGrade (est.) | **D/F** |

**Climate issues:** Dense urban canyon fabric creates deep shaded alleys in some zones while others act as heat funnels. Extreme UTCI in exposed pedestrian routes during Hajj/Umrah season. No outdoor relief infrastructure despite being primary pilgrim pedestrian zone.

**Renovation thesis:** Highest land value per m² in the portfolio — any outdoor comfort improvement multiplies directly on premium hospitality conversion value. Boutique Umrah accommodation repositioning. Pilgrim experience quality is a direct function of street-level thermal comfort.

```python
jarwal_polygon = {
    "type": "Polygon",
    "coordinates": [[
        [39.8072, 21.4228],
        [39.8212, 21.4228],
        [39.8212, 21.4328],
        [39.8072, 21.4328],
        [39.8072, 21.4228]
    ]]
}
```

---

### Asset 3 — Mikrorayon Alatau | Astana, Kazakhstan (Right Bank)

```
Centerpoint:      51.1800°N,  71.4550°E
SDK coordinates:  [71.4550, 51.1800]   ← GeoJSON [lng, lat]
District:         Almaty District, Right Bank (former Tselinograd core)
Building stock:   Soviet khrushchevki (5-story) + panel blocks (9-story), 1960s–1980s
Scale:            15–20 residential blocks, several thousand units
```

| Metric | Value |
|---|---|
| Current price/m² | KZT 380,000–520,000 · **$800–$1,095** |
| Post-renovation price/m² | KZT 550,000–700,000 · **$1,158–$1,474** |
| Value uplift | **+35–45%** |
| ClimateGrade (est.) | **D** |

**Climate issues:** NW Buran wind hits block facades broadside (Soviet standard N-S orientation). Wind amplification 1.4–1.8x ambient in inter-block corridors. December direct sun: ~2.8h/day vs. 4.5h residential benchmark — mutual shadowing between 9-story blocks. Courtyards are thermally hostile Oct–Apr.

**Renovation thesis:** City expanded around these blocks — now centrally located. Nurly Zhol national program covers 50–70% of renovation capex. Post-renovation units enter the mid-market rental pool at the top of their segment. Priority candidate for program funding given severe climate metrics.

```python
alatau_polygon = {
    "type": "Polygon",
    "coordinates": [[
        [71.4350, 51.1700],
        [71.4750, 51.1700],
        [71.4750, 51.1900],
        [71.4350, 51.1900],
        [71.4350, 51.1700]
    ]]
}
```

---

### Asset 4 — Yessil Tower Cluster | Astana, Kazakhstan (Left Bank)

```
Centerpoint:      51.1290°N,  71.4229°E
SDK coordinates:  [71.4229, 51.1290]   ← GeoJSON [lng, lat]
District:         Yessil District, Left Bank — Nurzhol Boulevard area
Building stock:   Premium high-rise towers, 20–30 stories, built 2005–2015
Scale:            8–12 towers within ~400m radius
```

| Metric | Value |
|---|---|
| Current price/m² | KZT 600,000–900,000 · **$1,263–$1,895** |
| Post-renovation price/m² | KZT 850,000–1,200,000 · **$1,789–$2,526** |
| Value uplift | **+35–42%** |
| ClimateGrade (est.) | **C/D** |

**Climate issues:** Tower spacing creates severe Venturi effect corridors — wind accelerates 1.6–2.2x between 25-story towers. Lawson pedestrian wind comfort fails for standing/walking Oct–Apr. Outdoor amenity zones (lobby approaches, courtyards, children's play areas) effectively unusable 5+ months/year despite premium address positioning.

**Renovation thesis:** Highest $/m² residential addresses in Kazakhstan. Building management associations are funded and motivated. Wind corridor mitigation (targeted canopies, vegetation screens, surface redesign) requires no structural change — interventions are low-capex, high-impact. Grade improvement is a direct marketing differentiator in a competitive premium market.

```python
yessil_polygon = {
    "type": "Polygon",
    "coordinates": [[
        [71.4029, 51.1190],
        [71.4429, 51.1190],
        [71.4429, 51.1390],
        [71.4029, 51.1390],
        [71.4029, 51.1190]
    ]]
}
```

---

## CONSOLIDATED ASSET REFERENCE

| # | Asset | City | Coordinates (lat, lng) | $/m² now | $/m² post-reno | Uplift | Grade |
|---|---|---|---|---|---|---|---|
| 1 | Al-Aziziyah District | Mecca | `21.4166, 39.8551` | $2,270–$3,200 | $4,000–$5,870 | **+70–83%** | F |
| 2 | Jarwal Neighborhood | Mecca | `21.4278, 39.8142` | $4,965–$6,940 | $6,940–$9,350 | **+35–40%** | D/F |
| 3 | Mikrorayon Alatau | Astana | `51.1800, 71.4550` | $800–$1,095 | $1,158–$1,474 | **+35–45%** | D |
| 4 | Yessil Tower Cluster | Astana | `51.1290, 71.4229` | $1,263–$1,895 | $1,789–$2,526 | **+35–42%** | C/D |

*Pricing sources: Numbeo May 2026, krisha.kz, aqar.fm*
*FX: 1 SAR = $0.267 · 1 KZT = $0.0021*

---

## SDK QUICK-START: ALL FOUR ASSETS

```python
from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import (
    AnalysesName, WindModelRequest, ThermalComfortIndexRequest,
    DirectSunHoursRequest, SkyViewFactorsRequest
)

ASSETS = {
    "al_aziziyah": {
        "city_profile": "riyadh",   # extreme heat profile
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[39.8451,21.4086],[39.8651,21.4086],
                              [39.8651,21.4246],[39.8451,21.4246],[39.8451,21.4086]]]
        }
    },
    "jarwal": {
        "city_profile": "riyadh",
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[39.8072,21.4228],[39.8212,21.4228],
                              [39.8212,21.4328],[39.8072,21.4328],[39.8072,21.4228]]]
        }
    },
    "alatau_mikrorayon": {
        "city_profile": "almaty",   # extreme cold + wind profile
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[71.4350,51.1700],[71.4750,51.1700],
                              [71.4750,51.1900],[71.4350,51.1900],[71.4350,51.1700]]]
        }
    },
    "yessil_towers": {
        "city_profile": "almaty",
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[71.4029,51.1190],[71.4429,51.1190],
                              [71.4429,51.1390],[71.4029,51.1390],[71.4029,51.1190]]]
        }
    }
}

# Run baseline analysis on any asset
async def run_baseline(asset_key: str):
    asset = ASSETS[asset_key]
    with InfraredClient() as client:

        # Preview cost first
        requests = [
            WindModelRequest(analysis_type=AnalysesName.wind_speed,
                             wind_speed=7, wind_direction=315),  # NW dominant
            ThermalComfortIndexRequest(),
            DirectSunHoursRequest(),
            SkyViewFactorsRequest()
        ]
        preview = client.preview_area_cost(requests, asset["polygon"])
        print(f"{asset_key}: estimated {preview.estimated_cost_tokens} tokens")

        # Run
        results = client.run_area_and_wait(
            requests,
            asset["polygon"]
        )
        return results
```

---

*Updated: 2026-05-29 | Added 4 candidate renovation assets: Mecca (Al-Aziziyah, Jarwal) + Astana (Alatau, Yessil)*

---

## FINANCIAL TRANSLATION MODEL

> Four sequential layers convert physics simulation grids into financial instruments
> that developers, lenders, and municipal budget committees understand.
> Implementation: `analysis/climate_financial_model.py`

---

### Layer 1 — Energy Cost Linkage

**Hypothesis:** Improving outdoor thermal comfort reduces HVAC load for adjacent
buildings via (a) lower outdoor UTCI → lower infiltration load and (b) better shading
→ lower solar gain through glazing.

#### Conversion rule-of-thumb

| Climate type | Conversion | Basis |
|---|---|---|
| Hot (Riyadh, Mecca) | 1 UTCI comfort-hour saved ≈ 0.8–1.2 kWh/m² cooling energy | DOE EnergyPlus calibration, Gulf region |
| Cold (Almaty, Astana) | 1 UTCI comfort-hour saved ≈ 0.6–0.9 kWh/m² heating energy | Kazakh SNiP building code benchmarks |

A "UTCI comfort-hour" = a cell-time-step where UTCI moves from outside to inside
the comfort band (−13 °C to +26 °C for moderate activity level).

#### Energy tariffs (2024 retail)

| Site | Energy type | Tariff | Source |
|---|---|---|---|
| Riyadh / Mecca | Cooling electricity | 0.048 SAR/kWh (~$0.013/kWh) | Saudi Electricity Company |
| Almaty | Heating (district) | KZT 18–22/kWh (~$0.040/kWh) | Almaty Teploset |
| Astana | Heating (gas + district) | KZT 22–28/kWh (~$0.055/kWh) | QazaqGaz retail |

#### From energy to asset value

```
delta_kwh_per_m2_yr  x  floor_area_m2  x  tariff  →  annual_utility_saving_USD
annual_utility_saving / cap_rate                    →  NOI_premium  →  asset_value_uplift
```

Typical cap rates: Riyadh Grade-A office 6.5 %, Almaty residential 8 %, Astana office 9 %.

---

### Layer 2 — Hedonic Pricing Regression

**Hypothesis:** Controlling for size, age, floor, and location, properties adjacent to
high-comfort public spaces command a measurable price premium.

#### Data sources

| Market | Platform | Fields |
|---|---|---|
| Astana / Almaty | krisha.kz | price_per_m2, floor, year, lat, lon, rooms |
| Riyadh | aqar.fm, bayut.com | price_per_m2, beds, year, lat, lon |
| Mecca / Jeddah | bayut.com | price_per_m2, beds, year, lat, lon |

#### Regression model

```
log(price_per_m2) = beta0
                  + beta1 * ClimateGrade_score        <- our simulation output
                  + beta2 * log(dist_to_metro_m)
                  + beta3 * floor
                  + beta4 * building_age
                  + beta5 * rooms
                  + epsilon
```

`ClimateGrade_score` = composite score (0–100) of nearest simulation polygon
centroid within 300 m.  Estimated with Ridge regression (alpha = 1.0) on scraped
listing data.  Reported as **"$ premium per 10-point score improvement per m²"**.

Expected coefficients (prior literature):
- Gulf residential: +$15–35/m² per 10 points
- Kazakh residential: +$8–18/m² per 10 points

---

### Layer 3 — Demand Signal Calibration

Hedonic regression captures *realised* prices only. Three proxy signals track
latent demand changes:

| Signal | Measure | Data source |
|---|---|---|
| Days on Market (DOM) | Median listing age for properties within 300 m | krisha.kz / aqar.fm scrape |
| Search velocity | NLP keyword frequency: "тень" (KZ), "ظل" / "هواء" (AR) in listing descriptions | Same scrape |
| Vacancy rate proxy | Fraction of listings re-listed within 90 days without sale | Rolling listing history |

These serve as **calibration anchors** for Layer 2:
- DOM 40% lower near high-score sites → confirms hedonic premium is real
- Rising search velocity → increase weight on solar/shade in scoring model

---

### Layer 4 — Climate Risk Discount & RCP Scenarios

**Hypothesis:** Properties dependent on current urban form for thermal comfort face a
growing risk discount as air temperatures rise — potentially becoming stranded assets
when UTCI exceeds habitability thresholds for >N weeks/year.

#### CMIP6 temperature deltas (2050 vs 2020, annual mean)

| Site | RCP 2.6 | RCP 4.5 | RCP 8.5 | Source |
|---|---|---|---|---|
| Riyadh | +1.1 °C | +1.8 °C | +3.2 °C | CMIP6 ensemble median |
| Mecca | +1.2 °C | +1.9 °C | +3.4 °C | CMIP6 |
| Almaty | +1.4 °C | +2.3 °C | +4.1 °C | CMIP6 |
| Astana | +1.6 °C | +2.7 °C | +4.8 °C | CMIP6 |

#### UTCI sensitivity to air temperature

Empirical: **delta_T_air +1 °C → delta_UTCI +0.7 °C**
(mid-latitude continental climates; UTCI-A dataset, Blazejczyk 2021)

#### Stranded asset threshold

```python
# Asset flagged as stranded-risk when ANY of:
projected_utci_mean_2050_rcp45 > 46.0    # extreme heat stress (WHO threshold)
frac_utci_bad_2050_rcp45       > 0.85    # 85% of hours outside comfort band

# Discount formula:
value_discount = min(0.25, 0.05 * years_above_threshold)
```

---

### Combined Output: Renovation NPV Calculator

```
Inputs:
  capex_usd           renovation cost
  site_key            "riyadh" | "almaty" | "astana" | "mecca"
  scenario_key        "A" | "B" | "C" | "D"
  floor_area_m2       total GFA of adjacent buildings within 300 m

Outputs:
  annual_energy_saving_usd
  hedonic_uplift_total_usd    = coeff * score_delta * floor_area_m2
  demand_premium_usd          = vacancy_reduction_factor * avg_rent * floor_area_m2
  climate_risk_avoided_usd    = (rcp45_discount - rcp26_discount) * total_asset_value
  total_value_usd             = sum of above
  npv_usd                     = total_value_usd - capex_usd
  roi_pct                     = npv_usd / capex_usd * 100
```

**Reference example — Riyadh Scenario B (shade sails):**
```
Capex:                  $180,000
Energy saving:          $42,000/yr  ->  NPV $310K @ 8% discount rate
Hedonic uplift:         $220K  (12,000 m2 GFA x $18.3/m2)
Demand premium:         $48K
Climate risk avoided:   $42K
─────────────────────────────────
Total value:            $620,000
ROI:                    244%
```

---

### Portfolio Climate Risk Report (per site)

```
Site name
  Current:   grade, composite score, UTCI mean, frac_bad
  2050 RCP2.6:  projected UTCI mean, frac_bad, stranded_flag
  2050 RCP4.5:  (same)
  2050 RCP8.5:  (same)
  Recommended intervention  +  payback period  +  capex range
```

---

### Lender Climate Scorecard (one-page PDF per loan application)

- Physical climate metrics: wind / sun / UTCI current
- Energy efficiency rating: A–F
- Projected value retention under RCP 4.5 (% of current appraisal)
- Recommended renovation capex to maintain investment grade
- Stranded-asset risk flag with threshold year

---

### Implementation Plan

| Layer | Class method | Status |
|---|---|---|
| Layer 1 — Energy | `energy_savings_annual()`, `value_from_energy()` | Scaffolded |
| Layer 2 — Hedonic | `fit_hedonic()`, `predict_uplift()` | Scaffolded |
| Layer 3 — Demand | `dom_signal()`, `search_velocity()`, `vacancy_proxy()` | Scaffolded |
| Layer 4 — Climate risk | `climate_risk_score()`, `stranded_asset_flag()` | Scaffolded |
| Combined | `renovation_npv()`, `portfolio_report()` | Scaffolded |

Source: `analysis/climate_financial_model.py`
