"""
generate_financial_data.py
─────────────────────────────────────────────────────────────────────────────
Auto-generates public/financial_data.json from renovation_data.json, using
each site's best_intervention scenario key and the site-specific market
parameters defined in SITE_PARAMS below.

Run AFTER:  export_web.py  (which produces renovation_data.json)

Usage:
    python generate_financial_data.py

Workflow note
─────────────
After any pipeline re-run (baseline → scenarios → score → export_web) that
changes best_intervention.key or UTCI improvement values, run this script
to refresh the financial numbers shown in the React dashboard finance strip
and Finance panel.  The physical scenario labels in the two footer rows will
stay in sync automatically.

Calibration
───────────
Adjust SITE_PARAMS with local listing data when available:
  • price_per_m2     — current market price (USD/m²)
  • annual_rent_psm  — achieved gross rent (USD/m²/yr)
  • floor_area_m2    — GFA of the buildings served by the public space
  • capex_usd        — estimated civil works cost for the chosen intervention
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ANALYSIS_DIR = Path(__file__).parent
PUBLIC_DIR   = ANALYSIS_DIR.parent / "public"

# ── Site market parameters ────────────────────────────────────────────────────
# Adjust with local listing-data when available.
SITE_PARAMS: dict[str, dict] = {
    "riyadh": {
        "floor_area_m2":     12_000,   # m² GFA served
        "capex_usd":        180_000,   # civil works (Scenario D canopy)
        "price_per_m2":       2_500,   # $/m² current market
        "annual_rent_psm":      160,   # $/m²/yr gross rent
    },
    "mecca": {
        "floor_area_m2":     10_000,
        "capex_usd":        200_000,
        "price_per_m2":       4_000,
        "annual_rent_psm":      220,
    },
    "almaty": {
        "floor_area_m2":      8_000,
        "capex_usd":         90_000,
        "price_per_m2":         900,
        "annual_rent_psm":       60,
    },
    "astana": {
        "floor_area_m2":     10_000,
        "capex_usd":        120_000,
        "price_per_m2":       1_100,
        "annual_rent_psm":       70,
    },
}


def _load_best_scenarios() -> dict[str, str]:
    """Return {site_key: scenario_key} from renovation_data.json."""
    reno_path = PUBLIC_DIR / "renovation_data.json"
    if not reno_path.exists():
        raise FileNotFoundError(
            f"{reno_path} not found — run export_web.py first"
        )
    with open(reno_path, encoding="utf-8") as f:
        reno = json.load(f)
    best: dict[str, str] = {}
    for site in reno.get("sites", []):
        bi = site.get("best_intervention") or {}
        key = bi.get("key")
        if key:
            best[site["key"]] = key
    return best


def generate(site_params: dict | None = None) -> dict:
    """
    Compute renovation NPV for every site and return the result dict.
    Pass a custom site_params mapping to override SITE_PARAMS defaults.
    """
    import sys
    sys.path.insert(0, str(ANALYSIS_DIR))
    from climate_financial_model import ClimateFinancialModel

    params = site_params or SITE_PARAMS
    best   = _load_best_scenarios()

    print("\n=== Generating financial_data.json ===")
    print(f"  Best scenarios from renovation_data.json: {best}")

    result: dict = {}
    for site_key, p in params.items():
        scenario_key = best.get(site_key)
        if not scenario_key:
            print(f"  [{site_key}] no best_intervention found — skipping")
            continue

        model = ClimateFinancialModel(site_key)
        npv   = model.renovation_npv(
            capex_usd            = p["capex_usd"],
            scenario_key         = scenario_key,
            floor_area_m2        = p["floor_area_m2"],
            price_per_m2_current = p["price_per_m2"],
            annual_rent_psm      = p["annual_rent_psm"],
        )
        e  = npv.energy
        cr = npv.climate_risk_rcp45

        result[site_key] = {
            "capex_usd":                p["capex_usd"],
            "scenario_key":             npv.scenario_key,
            "floor_area_m2":            p["floor_area_m2"],
            "annual_energy_saving_usd": round(npv.annual_energy_saving_usd, 0),
            "hedonic_uplift_usd":       round(npv.hedonic_uplift_usd, 0),
            "demand_premium_usd":       round(npv.demand_premium_usd, 0),
            "climate_risk_avoided_usd": round(npv.climate_risk_avoided_usd, 0),
            "total_value_usd":          round(npv.total_value_usd, 0),
            "npv_usd":                  round(npv.npv_usd, 0),
            "roi_pct":                  round(npv.roi_pct, 1),
            "delta_utci_c":             round(e.delta_utci_c, 3),
            "delta_kwh_m2_yr":          round(e.delta_kwh_per_m2_yr, 2),
            "stranded_rcp45":           cr.stranded_flag,
            "projected_utci_2050":      round(cr.projected_utci_mean_c, 1),
            "rcp45_discount_frac":      round(cr.value_discount_frac, 3),
        }

        r = result[site_key]
        print(
            f"  [{site_key}] Scenario {scenario_key}: "
            f"NPV ${r['npv_usd']:,.0f}  ROI {r['roi_pct']:.0f}%  "
            f"dUTCI {r['delta_utci_c']:+.3f}C"
            f"{'  ** STRANDED **' if r['stranded_rcp45'] else ''}"
        )

    return result


def main():
    result = generate()

    out = PUBLIC_DIR / "financial_data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n  Wrote {out}")
    print("  Reload the Vite dev server to pick up the new data.\n")


if __name__ == "__main__":
    main()
