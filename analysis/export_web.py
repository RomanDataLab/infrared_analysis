"""
RenovationMap -- Track C prep: Export web assets
=================================================
Copies baseline + scenario PNGs into public/heatmaps/<site>/
and writes public/renovation_data.json consumed by the React frontend.

Usage:
    python export_web.py

Run AFTER: baseline.py (both sites), scenarios.py (both sites),
           canopy_scenario.py (Riyadh), score.py --compare, batch.py
"""

import json, shutil
from datetime import date
from pathlib import Path
from sites import SITES

ANALYSIS_DIR = Path(__file__).parent
PUBLIC_DIR   = ANALYSIS_DIR.parent / "public"
HEATMAPS_DIR = PUBLIC_DIR / "heatmaps"

# PNGs to copy (missing ones are silently skipped)
PNG_NAMES = [
    # Thumbnails (with colorbar/title — used in ScoreCard)
    "baseline_wind.png",
    "baseline_sun.png",
    "baseline_utci.png",
    "batch_overview.png",
    "scenario_A_wind.png",      "scenario_A_utci.png",
    "scenario_A_delta_wind.png","scenario_A_delta_utci.png",
    "scenario_B_utci.png",      "scenario_B_delta_utci.png",
    "scenario_C_wind.png",      "scenario_C_utci.png",
    "scenario_C_delta_wind.png","scenario_C_delta_utci.png",
    "scenario_D_wind.png",      "scenario_D_utci.png",
    "scenario_D_delta_wind.png","scenario_D_delta_utci.png",
    # Overlay PNGs (pure grid, transparent NaN — used by Leaflet imageOverlay)
    "baseline_wind_overlay.png",
    "baseline_sun_overlay.png",
    "baseline_utci_overlay.png",
]


def copy_heatmaps(site_key):
    src = ANALYSIS_DIR / "results" / site_key
    dst = HEATMAPS_DIR / site_key
    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in PNG_NAMES:
        s = src / name
        if s.exists():
            shutil.copy2(s, dst / name)
            copied.append(name)
    print(f"  [{site_key}] copied {len(copied)} PNG(s)")
    return copied


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def build_site_entry(site_key, score, copied_pngs):
    if not score:
        return None
    site = SITES[site_key]
    heatmaps = {}
    for name in copied_pngs:
        stem = name.replace(".png", "")
        heatmaps[stem] = f"heatmaps/{site_key}/{name}"

    # Actual grid bounds from the API (tile-snapped) — [W, S, E, N] = [min_lng, min_lat, max_lng, max_lat]
    # Used by the Leaflet imageOverlay so the heatmap aligns with real geography.
    bounds_path = ANALYSIS_DIR / "results" / site_key / "baseline_bounds.json"
    overlay_bounds = None
    if bounds_path.exists():
        with open(bounds_path) as f:
            bd = json.load(f)
        overlay_bounds = bd.get("utci")   # [W, S, E, N]

    return {
        "key":             site_key,
        "name":            score["site_name"],
        "lat":             site["lat"],
        "lon":             site["lon"],
        "overlay_bounds":  overlay_bounds,   # [W, S, E, N] — None if not yet run
        "composite_score": score["composite_score"],
        "grade":           score["grade"],
        "grade_short":     score["grade"].split()[0],
        "climate":         score["climate"],
        "components":      score.get("components", {}),
        "key_stats":       score.get("key_stats", {}),
        "best_intervention": score.get("best_intervention"),
        "all_scenarios":   score.get("all_scenarios", {}),
        "heatmaps":        heatmaps,
    }


def main():
    PUBLIC_DIR.mkdir(exist_ok=True)
    HEATMAPS_DIR.mkdir(exist_ok=True)

    print("\n=== Exporting web assets ===")
    print(f"  Target: {PUBLIC_DIR}")

    sites_data = []
    batch_data = []

    for site_key in SITES:
        copied = copy_heatmaps(site_key)
        score  = load_json(ANALYSIS_DIR / "results" / site_key / "courtyard_score.json")
        batch  = load_json(ANALYSIS_DIR / "results" / site_key / "batch_results.json") or []
        entry  = build_site_entry(site_key, score, copied)
        if entry:
            sites_data.append(entry)
        batch_data.extend(batch)

    # Sort sites worst-first for the frontend ranking
    sites_data.sort(key=lambda x: x["composite_score"], reverse=True)
    batch_data.sort(key=lambda x: x["composite"], reverse=True)

    renovation_data = {
        "generated": str(date.today()),
        "sites":     sites_data,
        "batch":     batch_data,
    }

    out = PUBLIC_DIR / "renovation_data.json"
    with open(out, "w") as f:
        json.dump(renovation_data, f, indent=2)

    print(f"\n  Wrote renovation_data.json")
    print(f"    {len(sites_data)} main sites, {len(batch_data)} batch courtyards")

    # ── Auto-generate financial_data.json ──────────────────────────────────
    try:
        from generate_financial_data import generate
        fin = generate()
        fin_out = PUBLIC_DIR / "financial_data.json"
        with open(fin_out, "w", encoding="utf-8") as fh:
            json.dump(fin, fh, indent=2)
        print(f"\n  Wrote financial_data.json ({len(fin)} sites)")
    except Exception as exc:
        print(f"\n  [warn] financial_data.json not updated: {exc}")

    print(f"\n  To rebuild the map run:")
    print(f"    npm run dev   (inside {ANALYSIS_DIR.parent})")


if __name__ == "__main__":
    main()
