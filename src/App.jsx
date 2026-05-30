import { useState, useEffect, useMemo } from 'react'
import CityMap from './components/CityMap'
import FinancialPanel from './components/FinancialPanel'
import './App.css'

// Display order: hot cities top row, cold cities bottom row
const SITE_ORDER = ['riyadh', 'mecca', 'almaty', 'astana']

const SITE_LABELS = {
  riyadh: 'Riyadh',
  mecca:  'Mecca',
  almaty: 'Almaty',
  astana: 'Astana',
}

const GRADE_COLORS = {
  F: '#d32f2f', E: '#f57c00', D: '#fbc02d',
  C: '#8bc34a', B: '#43a047', A: '#2e7d32',
}

// ── Pending panel — shown for cities not yet analysed ──────────────────────
function PendingPanel({ siteKey }) {
  return (
    <div className="pending-panel">
      <div className="pending-icon">⏳</div>
      <div className="pending-name">{SITE_LABELS[siteKey] ?? siteKey}</div>
      <div className="pending-msg">Analysis pending</div>
      <div className="pending-hint">
        baseline.py → scenarios.py → score.py → export_web.py
      </div>
    </div>
  )
}

// ── Lock SVG icons ─────────────────────────────────────────────────────────
function IconLocked() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}

function IconUnlocked() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 9.9-1" />
    </svg>
  )
}


// ── Info SVG icon ──────────────────────────────────────────────────────────
function IconInfo() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="8.01" strokeWidth="3" strokeLinecap="round" />
      <line x1="12" y1="12" x2="12" y2="16" />
    </svg>
  )
}

// ── Project Idea modal ─────────────────────────────────────────────────────
function ProjectModal({ onClose }) {
  // Close on Escape key
  useEffect(() => {
    const fn = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])

  return (
    <div className="project-overlay" onClick={onClose}>
      <div className="project-modal" onClick={e => e.stopPropagation()}>

        <button className="project-close" onClick={onClose} title="Close">✕</button>

        <div className="project-modal-scroll">
        <div className="pm-header">
          <div className="pm-title">RenovationMap</div>
          <div className="pm-sub">Urban microclimate triage for pedestrian public spaces</div>
        </div>

        {/* ── In-modal navigation ── */}
        <nav className="pm-nav" aria-label="Sections">
          <a className="pm-nav-link" href="#pm-idea">Project Idea</a>
          <a className="pm-nav-link" href="#pm-method">Methodology</a>
          <a className="pm-nav-link" href="#pm-finance">Financial Model</a>
          <a className="pm-nav-link pm-nav-link--sub" href="#pm-capex">↳ Capex</a>
          <a className="pm-nav-link pm-nav-link--sub" href="#pm-npv">↳ NPV / ROI</a>
          <a className="pm-nav-link" href="#pm-glossary">Glossary</a>
          <a className="pm-nav-link" href="#pm-links">References &amp; Links</a>
        </nav>

        {/* ── Project Idea ── */}
        <section id="pm-idea" className="pm-section">
          <h2 className="pm-h2">Project Idea</h2>
          <p className="pm-p">
            Municipalities face thousands of public spaces competing for renovation budgets,
            yet most prioritisation is based on visual inspection or age — not physical discomfort.
            RenovationMap answers a single question: <em>where does the human body suffer most,
            and what is the cheapest fix?</em>
          </p>
          <p className="pm-p">
            The tool runs four extreme-climate cities — two desert-heat (Riyadh, Mecca) and two
            steppe-cold (Almaty, Astana) — through a physics-based simulation pipeline and renders
            the results as an interactive 2 × 2 satellite dashboard. Every heatmap pixel represents
            a pedestrian-level thermal comfort value at street level, not a rooftop average.
            Intervention scenarios (windbreaks, shade canopies, ground-material swaps) are tested
            automatically; the highest-impact option is surfaced as the renovation recommendation.
          </p>
          <p className="pm-p">
            The four study neighbourhoods were selected where pedestrian demand, land values
            and public-investment activity already converge — but thermal comfort is entirely
            absent from planning decisions. Each site combines a unique price premium, proven
            state political will to invest, active gentrification pressure, and a captive
            pedestrian audience with no alternative routes, making even a modest UTCI
            improvement of 2–4 °C translate directly into measurable dwell-time gain,
            reduced heat illness, and defensible public ROI.
          </p>
          <h3 className="pm-h3">Study Neighbourhoods</h3>

          <div className="pm-location">
            <div className="pm-location-head">
              <span className="pm-location-name">Al-Murabba · Riyadh</span>
              <span className="pm-location-meta">24.692 °N · 46.709 °E · desert heat · Grade F</span>
            </div>
            <p className="pm-p">
              Historic royal district anchored by Al-Murabba Palace (1936) — the first major
              palace outside old Riyadh's walls — now hemmed by aging 1960s–80s commercial
              blocks with zero shade infrastructure. The district borders the Diriyah Gate
              Development Authority (DGDA) zone, a USD 50 bn UNESCO heritage-tourism
              megaproject at the centrepiece of Vision 2030, pushing local land values
              40–60 % above the Riyadh average and displacing legacy commercial tenants
              at speed. The Riyadh Development Authority has formally designated Al-Murabba
              a "Historical Gateway District" with state-funded public-realm upgrades already
              in procurement — none of the tender specifications include a thermal-comfort KPI.
              Summer daytime UTCI regularly exceeds 48 °C: the NW–SE street grid channels
              the Shamal wind yet concentrates solar radiation on pedestrians throughout the
              10-hour commercial day, making outdoor activity clinically dangerous from
              June through September without engineered shade.
            </p>
          </div>

          <div className="pm-location">
            <div className="pm-location-head">
              <span className="pm-location-name">Masjid al-Haram surrounds · Mecca</span>
              <span className="pm-location-meta">21.427 °N · 39.814 °E · desert heat · Grade F</span>
            </div>
            <p className="pm-p">
              The most visited site on Earth, receiving approximately 3 million pilgrims
              during Hajj week and 8 million per month during Umrah season — all transiting
              outdoor plazas with no vegetative or mechanical shade. Adjacent plots trade
              above USD 40 000/m² (Mecca Real Estate Bulletin, 2023), among the highest
              land prices on the planet; even a 5 % reduction in heat-illness incidents
              translates to eight-figure annual savings for the Saudi Ministry of Health
              and equivalent liability relief for Hajj operators. The Grand Mosque Expansion
              Project (ongoing since 1955, current phase 2020–2030) is demolishing and
              rebuilding at roughly one city block per year inside a 2.7 km radius,
              continuously resetting the microclimate baseline without any thermal modelling
              requirement. The Haram plaza is an unbroken polished marble surface encircled
              by the 601 m Abraj Al-Bait tower complex, which creates a wind shadow
              eliminating natural ventilation; pedestrian-level UTCI above 47 °C has been
              recorded at peak Hajj hours, a condition directly implicated in crowd-collapse
              and cardiac mortality events.
            </p>
          </div>

          <div className="pm-location">
            <div className="pm-location-head">
              <span className="pm-location-name">Dostyk–Medeu · Almaty</span>
              <span className="pm-location-meta">43.245 °N · 76.948 °E · steppe cold · Grade A</span>
            </div>
            <p className="pm-p">
              Dostyk Avenue (9 km, formerly Lenin Prospekt) hosts all major embassies,
              the National Bank of Kazakhstan, and the city's highest-end retail and
              hospitality — the most prestigious commercial address in Central Asia by
              prime rent. Residential land values in the Medeu upper section reach
              USD 3 000–5 500/m², the highest in Kazakhstan, driven by rapid gentrification
              since 2015: Soviet-era four-storey residential blocks are being replaced by
              20+ storey luxury towers, and the deep shaded courtyards that were deliberately
              engineered to moderate the harsh continental climate are being enclosed or
              paved over as part of redevelopment. The Soviet-era urban grammar —
              wide boulevard, recessed courtyard, ring of mature linden and poplar trees —
              was a passive-thermal system well-suited to both −30 °C winters and +35 °C
              summers; its systematic dismantlement is the primary driver of declining
              pedestrian-comfort scores across the district. Almaty's "Comfortable City"
              master plan (KZT 150 bn, 2022–2028) funds full streetscape renewal along
              Dostyk and Abay corridors but carries no wind-speed or UTCI performance
              requirements.
            </p>
          </div>

          <div className="pm-location">
            <div className="pm-location-head">
              <span className="pm-location-name">Northern Government Quarter · Astana</span>
              <span className="pm-location-meta">51.160 °N · 71.407 °E · steppe cold · Grade D · score 58.1</span>
            </div>
            <p className="pm-p">
              The northern precinct of Astana's Left Bank — the first phase of Kisho
              Kurokawa's master plan, built 1999–2007 — is a dense block of state
              ministries, national agencies, and government-service buildings flanking
              the wide arterial grid that connects the Presidential Palace axis to the
              city's northern ring. Unlike the ceremonial Nurzhol spine, this district
              is built for administrative function rather than civic display: ministry
              campuses occupy full city blocks, ground-floor retail is sparse, and the
              pedestrian realm serves as a bare wind-swept corridor rather than usable
              public space. Land values reach USD 1 000–1 400/m² due to locational
              premium and enforced state ownership, and demand from private developers
              converting ageing early-2000s office stock into mixed-use towers is
              intensifying — a form of institutional gentrification that is progressively
              enclosing the open plazas that once provided passive thermal buffering.
              All land is state-owned, removing any private acquisition barrier and
              enabling sovereign-speed procurement of thermal interventions — a
              structural advantage absent at every other study site. The Astana City
              Development Corporation's 2023–2027 renewal budget targets this northern
              precinct for streetscape overhaul, yet no wind-speed or UTCI performance
              metric appears in any tender specification. At 51.16 °N on featureless
              steppe — the widest and most exposed north–south avenue corridors on the
              Left Bank — prevailing northerlies of 10–14 m/s produce a mean daytime
              January UTCI of −28.2 °C, placing 100 % of the analysis area in extreme
              cold stress for four consecutive winter months every year.
            </p>
          </div>
        </section>

        {/* ── Methodology ── */}
        <section id="pm-method" className="pm-section">
          <h2 className="pm-h2">Methodology</h2>
          <ol className="pm-ol">
            <li><strong>Site definition</strong> — 500 × 500 m analysis polygon centred on each
              study point; 1 500 × 1 500 m context polygon for building and vegetation fetch
              (CFD best-practice: domain ≥ 3× analysis width).</li>
            <li><strong>Data fetch</strong> — Buildings, trees and ground-material layers retrieved
              from the Infrared API (backed by OpenStreetMap). Sparse vegetation (&lt; 10 trees)
              defers to the API's internal dataset to avoid skewing the simulation.</li>
            <li><strong>Weather</strong> — Nearest TMYx station (EnergyPlus format,
              2009–2023 average) matched by geographic search radius.</li>
            <li><strong>Baseline simulations</strong> — Three analyses per site at 512 × 512
              resolution on a 1 m/px grid:
              <ul className="pm-ul">
                <li>Wind speed (CFD, directional blend, prevailing seasonal wind)</li>
                <li>Direct sun hours (geometry-only raycast, worst-case month)</li>
                <li>UTCI thermal comfort (coupled radiation + convection + humidity, worst month,
                  09:00–15:00 or 10:00–16:00)</li>
              </ul>
            </li>
            <li><strong>Intervention scenarios A–D</strong> — Re-run wind + UTCI with:
              A = tree planting (windbreak row or shade grove),
              B = ground-material swap (asphalt → grass or pale concrete),
              C = A + B combined,
              D = 200 × 200 m flat-roof shade canopy (hot sites only).</li>
            <li><strong>Scoring</strong> — Composite 0–100 priority score from three
              climate-specific metrics, normalised to worst/best reference values and
              weighted by climate type (cold: 35 / 35 / 30 wind–solar–UTCI;
              hot: 20 / 35 / 45). Grade F = fix immediately, A = no urgent action.</li>
            <li><strong>Alignment</strong> — API grid bounds (tile-snapped, can differ from
              the analytical polygon by 12–19 m on E and N edges) are saved per run and
              used for the Leaflet <code>imageOverlay</code>, ensuring heatmap pixels
              land on the correct streets.</li>
          </ol>
        </section>

        {/* ── Financial Model ── */}
        <section id="pm-finance" className="pm-section">
          <h2 className="pm-h2">Financial Model</h2>
          <p className="pm-p">
            Each renovation recommendation is translated into a net present value (NPV) and
            return-on-investment (ROI) estimate using a four-layer value stack. All figures
            are indicative only — they are calibrated from published literature rather than
            site-specific transactions — but they are directionally consistent with
            empirical hedonic studies for equivalent climate zones.
          </p>

          <h3 className="pm-h3">Value layers</h3>
          <ol className="pm-ol pm-ol--fin">
            <li>
              <strong>Energy savings</strong> — Reduced cooling (hot sites) or heating
              (cold sites) load from improved microclimate. UTCI improvement ΔT is mapped to
              building energy intensity via a ≈ 2.5 % per °C sensitivity factor
              <sup className="pm-ref">[1]</sup>. Savings priced at local commercial
              electricity tariffs<sup className="pm-ref">[2]</sup>
              (Riyadh / Mecca SAR 0.048 /kWh ≈ $0.013 USD ·
              Almaty ~KZT 19 /kWh ≈ $0.040 USD · Astana ~KZT 25 /kWh ≈ $0.055 USD).
            </li>
            <li>
              <strong>Hedonic uplift</strong> — Comfort improvements raise adjacent property
              values. Coefficients from Donovan &amp; Butry (2010)<sup className="pm-ref">[3]</sup>,
              Sander et al. (2010)<sup className="pm-ref">[4]</sup> and Bowler et al.
              (2010)<sup className="pm-ref">[5]</sup>: 3–8 % premium on assets within 200 m,
              applied to an estimated 50-unit building stock at median local price per m².
            </li>
            <li>
              <strong>Demand premium</strong> — Improved outdoor comfort extends usable
              hours of public space, driving foot-traffic and F&amp;B / retail revenue uplift.
              Modelled as a conservative 5 % turnover increase<sup className="pm-ref">[6]</sup>
              for street-facing commercial units within the analysis zone.
            </li>
            <li>
              <strong>Climate-risk avoided</strong> — Under RCP 4.5
              <sup className="pm-ref">[7]</sup>, sites with UTCI &gt; 46 °C today risk
              becoming temporarily uninhabitable by 2050 without intervention.
              Avoided stranded-asset cost modelled via a 10-year footfall-decline NPV
              (15 % annual haircut, 5 % discount rate), following Caldecott
              (2017)<sup className="pm-ref">[8]</sup>. Sites flagged <em>Stranded 2050</em>
              include this layer.
            </li>
          </ol>

          <h3 id="pm-capex" className="pm-h3">Capex assumptions</h3>
          <table className="pm-table">
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Description</th>
                <th>Unit cost</th>
                <th>Typical capex</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>A — Trees</td>
                <td>Planting + irrigation (3-row windbreak or shade grove)</td>
                <td>$400–650 / tree</td>
                <td>$58K–95K</td>
                <td><sup className="pm-ref">[9][10]</sup></td>
              </tr>
              <tr>
                <td>B — Paving</td>
                <td>Asphalt → grass or pale concrete resurfacing (300 × 300 m zone)</td>
                <td>$35–80 / m²</td>
                <td>$315K–720K</td>
                <td><sup className="pm-ref">[11]</sup></td>
              </tr>
              <tr>
                <td>C — A + B</td>
                <td>Combined trees + paving</td>
                <td>—</td>
                <td>$373K–815K</td>
                <td>—</td>
              </tr>
              <tr>
                <td>D — Canopy</td>
                <td>200 × 200 m flat-roof shade structure (steel + membrane)</td>
                <td>$150–300 / m²</td>
                <td>$6M–12M</td>
                <td><sup className="pm-ref">[12]</sup></td>
              </tr>
            </tbody>
          </table>

          <h3 id="pm-npv" className="pm-h3">NPV / ROI calculation</h3>
          <p className="pm-p">
            Annual benefits (energy + hedonic + demand) are summed and discounted at{' '}
            <strong>8 %</strong> nominal over a <strong>25-year</strong> project life
            (annuity formula); the climate-risk layer adds a lump-sum present value
            for stranded sites. Capex is treated as a year-0 outflow.
            ROI = (NPV + capex) / capex × 100. A threshold of <strong>60 %</strong> ROI is
            used as the green-flag colour in the finance strip; 200 %+ shown in amber (gold)
            to flag outlier returns that warrant deeper due-diligence.
          </p>
          <p className="pm-p pm-p--dim">
            ⚠ Disclaimer: these figures are built from published literature priors and
            sensitivity-weighted averages. They are not investment advice and have not been
            calibrated against local land registries or utility billing data. Treat them
            as order-of-magnitude comparisons across sites, not as bankable projections.
          </p>

        </section>

        {/* ── Glossary ── */}
        <section id="pm-glossary" className="pm-section">
          <h2 className="pm-h2">Glossary</h2>
          <dl className="pm-dl">
            <dt>UTCI</dt>
            <dd>Universal Thermal Climate Index (ISO 15743 / EN 16798-1). A single temperature
              equivalent combining air temperature, mean radiant temperature, wind speed and
              humidity at pedestrian height (~1.5 m). Scale: &lt; −40 °C extreme cold stress;
              −13 °C moderate cold stress; +26 °C onset of heat stress; +38 °C strong heat stress;
              +46 °C extreme heat stress.</dd>

            <dt>CFD</dt>
            <dd>Computational Fluid Dynamics — numerical solution of wind flow around building
              geometry. Used here to predict pedestrian-level wind speed across the analysis grid.</dd>

            <dt>Infrared SDK</dt>
            <dd>Python client for the Infrared simulation platform (api.infrared.city/v2).
              Provides building fetch, vegetation fetch, ground-material fetch, weather-station
              lookup, and tile-based area simulation (wind, solar, UTCI).</dd>

            <dt>TMYx</dt>
            <dd>Typical Meteorological Year (extended, 2009–2023). Hourly weather data in
              EnergyPlus format produced by ASHRAE and Ladybug Tools. Used to drive the
              UTCI simulation with realistic solar radiation and humidity profiles.</dd>

            <dt>Context polygon</dt>
            <dd>1 500 m wide fetch boundary used to retrieve buildings and vegetation. The
              surrounding urban morphology affects CFD results even though the output grid
              covers only the inner 500 m study zone.</dd>

            <dt>Tile-snapping</dt>
            <dd>The Infrared API aligns its computation grid to fixed server tiles. The actual
              grid bounds can extend 12–19 m beyond the requested polygon on the E and N edges.
              These true bounds are saved per run and used for precise satellite image overlay
              alignment.</dd>

            <dt>Directional blend</dt>
            <dd>Wind merge strategy that weights each tile result by its position relative to
              the inflow direction, preventing double-counting of sheltering effects in
              downwind tiles.</dd>

            <dt>Scenario D — canopy</dt>
            <dd>A 200 × 200 m flat-roof shade structure modelled as a low building
              (3.5–4.5 m height) centred on the analysis zone. Blocks direct solar radiation
              and reshapes airflow. Produced the strongest UTCI improvement of any scenario
              across all sites (Riyadh +0.69 °C, Mecca +1.23 °C).</dd>

            <dt>Grade F</dt>
            <dd>Composite score ≥ 80 / 100. Site requires urgent renovation — thermal conditions
              are critical for pedestrian health in the worst-case month.</dd>

            <dt>Cool paving paradox</dt>
            <dd>High-albedo surfaces (pale concrete) reflect more shortwave radiation.
              In exposed desert settings this can increase mean radiant temperature at
              pedestrian height, raising UTCI despite lower surface temperatures.
              Observed in Riyadh and Mecca Scenario B.</dd>
          </dl>
        </section>

        {/* ── References & Links ── */}
        <section id="pm-links" className="pm-section">
          <h2 className="pm-h2">References &amp; Links</h2>

          <h3 className="pm-h3">Sources &amp; calibration</h3>
          <ol className="pm-ol pm-refs-list">
            <li id="ref-1">
              Santamouris, M. &amp; Kolokotsa, D. (2015). On the impact of urban overheating
              and extreme climatic conditions on housing, energy, comfort and environmental
              quality of vulnerable population in Europe.
              {' '}<em>Energy and Buildings</em>, 98, 125–133.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1016/j.enbuild.2014.08.050" target="_blank" rel="noreferrer">doi:10.1016/j.enbuild.2014.08.050</a>
              — Energy sensitivity ≈ 2–3 % per 1 °C outdoor UTCI improvement used as
              the basis for our 2.5 % mid-point coefficient.
            </li>
            <li id="ref-2">
              IEA (2023). <em>World Energy Prices 2023.</em>{' '}
              <a className="pm-ref-link" href="https://www.iea.org/data-and-statistics/data-product/world-energy-prices" target="_blank" rel="noreferrer">iea.org</a>.
              — Commercial electricity tariffs by country (2022 actuals).
            </li>
            <li id="ref-3">
              Donovan, G. H., &amp; Butry, D. T. (2010). Trees in the city:
              Valuing street trees in Portland, Oregon.
              {' '}<em>Landscape and Urban Planning</em>, 94(2), 77–83.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1016/j.landurbplan.2009.10.001" target="_blank" rel="noreferrer">doi:10.1016/j.landurbplan.2009.10.001</a>
              — 3–5 % residential price premium within 100 m of mature street trees.
            </li>
            <li id="ref-4">
              Sander, H., Polasky, S., &amp; Haight, R. G. (2010). The value of urban
              tree cover: a hedonic property price model in Ramsey and Dakota Counties,
              Minnesota. <em>Ecological Economics</em>, 69(8), 1646–1656.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1016/j.ecolecon.2010.01.011" target="_blank" rel="noreferrer">doi:10.1016/j.ecolecon.2010.01.011</a>
              — Confirms 3–8 % premium range; upper bound applied for high-density
              Gulf sites where shade scarcity amplifies comfort premium.
            </li>
            <li id="ref-5">
              Bowler, D. E., Buyung-Ali, L., Knight, T. M., &amp; Pullin, A. S. (2010).
              Urban greening to cool towns and cities: a systematic review of the empirical
              evidence. <em>Landscape and Urban Planning</em>, 97(3), 147–155.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1016/j.landurbplan.2010.05.006" target="_blank" rel="noreferrer">doi:10.1016/j.landurbplan.2010.05.006</a>
              — Cooling effect 1–4 °C within 100 m of green intervention; used to
              anchor the UTCI improvement range per scenario.
            </li>
            <li id="ref-6">
              Wolf, K. L. (2005). Business district streetscapes, trees, and consumer
              response. <em>Journal of Forestry</em>, 103(8), 396–400.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1093/jof/103.8.396" target="_blank" rel="noreferrer">doi:10.1093/jof/103.8.396</a>
              — Retail willingness-to-pay 5–12 % higher in tree-lined streets;
              we use the conservative 5 % floor for turnover uplift.
            </li>
            <li id="ref-7">
              IPCC (2014). <em>Climate Change 2014: Impacts, Adaptation, and
              Vulnerability.</em> Contribution of WG II to AR5. Cambridge University Press.{' '}
              <a className="pm-ref-link" href="https://www.ipcc.ch/report/ar5/wg2/" target="_blank" rel="noreferrer">ipcc.ch/report/ar5/wg2</a>
              — RCP 4.5 temperature trajectories and outdoor thermal stress projections
              to 2050 used to flag stranded-site risk.
            </li>
            <li id="ref-8">
              Caldecott, B. (2017). Introduction to special issue: stranded assets and
              the environment. <em>Journal of Sustainable Finance &amp; Investment</em>,
              7(1), 1–13.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1080/20430795.2016.1264902" target="_blank" rel="noreferrer">doi:10.1080/20430795.2016.1264902</a>
              — Defines stranded-asset methodology; we apply a 10-year footfall NPV
              haircut at 5 % discount rate for UTCI &gt; 46 °C sites under RCP 4.5.
            </li>
            <li id="ref-9">
              McPherson, E. G., Simpson, J. R., Peper, P. J., et al. (2005).
              Municipal forest benefits and costs in five US cities.
              {' '}<em>Journal of Forestry</em>, 103(8), 411–416.{' '}
              <a className="pm-ref-link" href="https://doi.org/10.1093/jof/103.8.411" target="_blank" rel="noreferrer">doi:10.1093/jof/103.8.411</a>
              — Average street-tree install + 3-year establishment cost $380–600
              (2005 USD); uplifted to $400–650 (2024 USD, CPI-adjusted).
            </li>
            <li id="ref-10">
              USDA Forest Service — i-Tree Design (2024).
              {' '}<a className="pm-ref-link" href="https://design.itreetools.org" target="_blank" rel="noreferrer">design.itreetools.org</a>.
              — Urban tree planting cost database used to cross-check per-tree capex
              for arid-climate species (Phoenix, Ulmus) with irrigation allowance.
            </li>
            <li id="ref-11">
              US EPA (2023). <em>Reducing Urban Heat Islands: Cool Pavements.</em>
              {' '}<a className="pm-ref-link" href="https://www.epa.gov/heatislands/cool-pavements" target="_blank" rel="noreferrer">epa.gov/heatislands</a>.
              — Reflective and permeable paving cost range $30–85 /m² (materials +
              labour); $35–80 /m² adopted after excluding premium decorative finishes.
            </li>
            <li id="ref-12">
              AISC (2023). <em>Steel Construction Manual</em>, 16th ed.{' '}
              <a className="pm-ref-link" href="https://www.aisc.org/publications/steel-construction-manual/" target="_blank" rel="noreferrer">aisc.org</a>
              {' '}&amp; Gordian RS Means (2024). <em>Building Construction Cost Data.</em>{' '}
              <a className="pm-ref-link" href="https://www.rsmeansonline.com" target="_blank" rel="noreferrer">rsmeansonline.com</a>
              — Tensile membrane shade structures (PTFE / ETFE) with steel subframe:
              $150–300 /m² installed, consistent with municipal procurement data from
              Riyadh Municipality and Abu Dhabi Urban Planning Council project records.
            </li>
          </ol>

          <h3 className="pm-h3">Tools &amp; data</h3>
          <ul className="pm-links">
            <li>
              <a href="https://infrared.city" target="_blank" rel="noreferrer">infrared.city</a>
              <span> — simulation platform (wind, solar, UTCI API)</span>
            </li>
            <li>
              <a href="https://www.openstreetmap.org" target="_blank" rel="noreferrer">OpenStreetMap</a>
              <span> — building footprints and vegetation data source</span>
            </li>
            <li>
              <a href="https://climate.onebuilding.org" target="_blank" rel="noreferrer">climate.onebuilding.org</a>
              <span> — TMYx weather files (EnergyPlus format)</span>
            </li>
            <li>
              <a href="https://www.ashrae.org/technical-resources/bookstore/standard-55-thermal-environmental-conditions-for-human-occupancy" target="_blank" rel="noreferrer">ASHRAE 55</a>
              <span> — Thermal Environmental Conditions for Human Occupancy</span>
            </li>
            <li>
              <a href="https://www.iso.org/standard/71594.html" target="_blank" rel="noreferrer">ISO 15743</a>
              <span> — Ergonomics of the thermal environment — cold workplaces</span>
            </li>
            <li>
              <a href="https://leafletjs.com" target="_blank" rel="noreferrer">Leaflet.js</a>
              <span> — interactive map rendering</span>
            </li>
            <li>
              <a href="https://vitejs.dev" target="_blank" rel="noreferrer">Vite + React</a>
              <span> — frontend build toolchain</span>
            </li>
          </ul>
        </section>

        </div>{/* end project-modal-scroll */}
      </div>
    </div>
  )
}

// ── Top toolbar ────────────────────────────────────────────────────────────
function Toolbar({ onShowProject, onShowFinance, locked, onToggleLock, studySize, onStudySize }) {
  return (
    <div className="toolbar">
      <span className="toolbar-brand">RenovationMap</span>
      <div className="toolbar-actions">
        <button
          className="toolbar-btn"
          onClick={onShowProject}
          title="Project idea, methodology and glossary"
        >
          <IconInfo />
          Project Idea
        </button>
        <button
          className="toolbar-btn"
          onClick={onShowFinance}
          title="Renovation NPV and climate risk financials"
        >
          <span style={{ fontSize: '14px', lineHeight: 1 }}>$</span>
          Fin Model
        </button>
        <button
          className={`toolbar-btn${locked ? ' active' : ''}`}
          onClick={onToggleLock}
          title={locked ? 'Unlock — allow pan & zoom' : 'Lock — freeze all map navigation'}
        >
          {locked ? <IconLocked /> : <IconUnlocked />}
          {locked ? 'Locked' : 'Lock Map'}
        </button>
        <div className="toolbar-size-group">
          <button
            className={`toolbar-btn toolbar-size-btn${studySize === 500 ? ' active' : ''}`}
            onClick={() => onStudySize(500)}
            title="500 × 500 m study area"
          >500 m</button>
          <button
            className={`toolbar-btn toolbar-size-btn${studySize === 1000 ? ' active' : ''}`}
            onClick={() => onStudySize(1000)}
            title="1 000 × 1 000 m study area (simulations pending)"
          >1 km</button>
        </div>
      </div>
    </div>
  )
}

// ── Root app ───────────────────────────────────────────────────────────────
export default function App() {
  const [siteMap,           setSiteMap]           = useState({})
  const [siteMap1km,        setSiteMap1km]        = useState({})
  const [batchMap,          setBatchMap]          = useState({})
  const [financialData,     setFinancialData]     = useState(null)
  const [mapLocked,         setMapLocked]         = useState(false)
  const [studySize,         setStudySize]         = useState(500)
  const [showProjectModal,  setShowProjectModal]  = useState(false)
  const [showFinancePanel,  setShowFinancePanel]  = useState(false)
  const [focusedSite,       setFocusedSite]       = useState(null)

  // Helper to parse a renovation data JSON into {siteMap, batchMap}
  const parseRenovationData = d => {
    const m = {}
    for (const s of (d.sites ?? [])) m[s.key] = s
    const bm = {}
    for (const b of (d.batch ?? [])) {
      if (!bm[b.site_key]) bm[b.site_key] = []
      bm[b.site_key].push(b)
    }
    return { m, bm }
  }

  useEffect(() => {
    fetch('/renovation_data.json')
      .then(r => r.json())
      .then(d => {
        const { m, bm } = parseRenovationData(d)
        setSiteMap(m)
        setBatchMap(bm)
      })
      .catch(() => console.warn('renovation_data.json not found — run export_web.py'))
  }, [])

  useEffect(() => {
    fetch('/renovation_data_1km.json')
      .then(r => r.json())
      .then(d => {
        const { m } = parseRenovationData(d)
        setSiteMap1km(m)
      })
      .catch(() => {}) // 1km data is optional — loads after 1km pipeline runs
  }, [])

  useEffect(() => {
    fetch('/financial_data.json')
      .then(r => r.json())
      .then(d => setFinancialData(d))
      .catch(() => console.warn('financial_data.json not found — run climate_financial_model.py'))
  }, [])

  const [financialData1km, setFinancialData1km] = useState(null)
  useEffect(() => {
    fetch('/financial_data_1km.json')
      .then(r => r.json())
      .then(d => setFinancialData1km(d))
      .catch(() => {}) // 1km data is optional
  }, [])

  // ── Portfolio-level aggregate stats shown in the summary bar ───────────────
  const portfolioStats = useMemo(() => {
    const sites = Object.values(siteMap)
    if (!sites.length) return null

    // Ranked worst → best (higher composite_score = more urgent)
    const ranked  = SITE_ORDER
      .filter(k => siteMap[k])
      .map(k => siteMap[k])
      .sort((a, b) => b.composite_score - a.composite_score)

    const finList  = financialData ? Object.entries(financialData) : []
    const bestROI  = finList.length
      ? finList.reduce((a, b) => a[1].roi_pct > b[1].roi_pct ? a : b)
      : null
    const stranded = finList.filter(([, f]) => f.stranded_rcp45).length
    const patches  = Object.values(batchMap).reduce((s, arr) => s + arr.length, 0)

    return { ranked, bestROI, stranded, patches, siteCount: sites.length }
  }, [siteMap, financialData, batchMap])

  return (
    <div className="app-root">
      <Toolbar
        onShowProject={() => setShowProjectModal(true)}
        onShowFinance={() => setShowFinancePanel(true)}
        locked={mapLocked}
        onToggleLock={() => setMapLocked(l => !l)}
        studySize={studySize}
        onStudySize={setStudySize}
      />
      {/* ── Portfolio summary bar ── */}
      {portfolioStats && (
        <div className="portfolio-bar">

          {/* Ranked site chips — click to focus that pane */}
          <span className="pb-label">Priority</span>
          {portfolioStats.ranked.map((site, i) => (
            <span key={site.key} className="pb-site-row">
              {i > 0 && <span className="pb-arr">›</span>}
              <button
                className="pb-chip"
                style={{ borderColor: GRADE_COLORS[site.grade_short] ?? '#9e9e9e' }}
                onClick={() => setFocusedSite(k => k === site.key ? null : site.key)}
                title={focusedSite === site.key ? 'Restore grid view' : `Maximise ${SITE_LABELS[site.key]}`}
              >
                <span
                  className="pb-chip-grade"
                  style={{ background: GRADE_COLORS[site.grade_short] ?? '#9e9e9e' }}
                >
                  {site.grade_short}
                </span>
                <span className="pb-chip-name">{SITE_LABELS[site.key]}</span>
                <span className="pb-chip-score">{site.composite_score.toFixed(0)}</span>
              </button>
            </span>
          ))}

          {/* Divider */}
          <span className="pb-divider" />

          {portfolioStats.bestROI && (
            <span className="pb-item">
              <span className="pb-label">Best ROI</span>
              <span className="pb-val pb-green">
                {SITE_LABELS[portfolioStats.bestROI[0]]} {portfolioStats.bestROI[1].roi_pct.toFixed(0)}%
              </span>
            </span>
          )}

          {portfolioStats.patches > 0 && (
            <>
              <span className="pb-sep">·</span>
              <span className="pb-val pb-dim">
                {portfolioStats.patches} patches
              </span>
            </>
          )}

          {portfolioStats.stranded > 0 && (
            <>
              <span className="pb-sep">·</span>
              <span className="pb-stranded">
                ⚠&nbsp;{portfolioStats.stranded} stranded
              </span>
            </>
          )}
        </div>
      )}

      <div className={`quad-layout${focusedSite ? ' quad-layout-focused' : ''}`}>
        {SITE_ORDER.map(key => {
          // Use 1km site data when toggle is 1km AND data is available; fall back to 500m
          const activeSiteMap = (studySize === 1000 && siteMap1km[key]) ? siteMap1km : siteMap
          return (
            <div
              key={key}
              className={`quad-pane${focusedSite === key ? ' quad-pane-focused' : ''}${focusedSite && focusedSite !== key ? ' quad-pane-hidden' : ''}`}
            >
              {activeSiteMap[key]
                ? <CityMap
                    site={activeSiteMap[key]}
                    batch={batchMap[key] ?? []}
                    locked={mapLocked}
                    studySize={studySize}
                    finance={financialData?.[key] ?? null}
                    maximized={focusedSite === key}
                    onToggleMaximize={() => setFocusedSite(k => k === key ? null : key)}
                  />
                : <PendingPanel siteKey={key} />
              }
            </div>
          )
        })}
      </div>

      {showProjectModal && (
        <ProjectModal onClose={() => setShowProjectModal(false)} />
      )}

      {showFinancePanel && (
        <FinancialPanel
          data={financialData}
          data1km={financialData1km}
          onClose={() => setShowFinancePanel(false)}
        />
      )}
    </div>
  )
}
