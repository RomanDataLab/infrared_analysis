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


def copy_heatmaps(site_key, size=500):
    subdir = "1km" if size == 1000 else ""
    src = ANALYSIS_DIR / "results" / site_key / (subdir or ".")
    dst = HEATMAPS_DIR / site_key / (subdir or ".")
    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in PNG_NAMES:
        s = src / name
        if s.exists():
            shutil.copy2(s, dst / name)
            copied.append(name)
    tag = f"{site_key}/1km" if size == 1000 else site_key
    print(f"  [{tag}] copied {len(copied)} PNG(s)")
    return copied


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def build_site_entry(site_key, score, copied_pngs, size=500):
    if not score:
        return None
    site    = SITES[site_key]
    subdir  = "1km" if size == 1000 else ""
    hm_root = f"heatmaps/{site_key}" + ("/1km" if size == 1000 else "")
    heatmaps = {}
    for name in copied_pngs:
        stem = name.replace(".png", "")
        heatmaps[stem] = f"{hm_root}/{name}"

    # Actual grid bounds — [W, S, E, N]
    bounds_path = ANALYSIS_DIR / "results" / site_key / (subdir or ".") / "baseline_bounds.json"
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


def export_size(size):
    """Export one size variant (500 or 1000). Returns (sites_data, batch_data)."""
    subdir = "1km" if size == 1000 else ""
    sites_data, batch_data = [], []
    for site_key in SITES:
        copied = copy_heatmaps(site_key, size)
        score_path = ANALYSIS_DIR / "results" / site_key / (subdir or ".") / "courtyard_score.json"
        score  = load_json(score_path)
        batch  = load_json(ANALYSIS_DIR / "results" / site_key / "batch_results.json") or []
        entry  = build_site_entry(site_key, score, copied, size)
        if entry:
            sites_data.append(entry)
        if size == 500:          # batch courtyards only in primary export
            batch_data.extend(batch)
    sites_data.sort(key=lambda x: x["composite_score"], reverse=True)
    return sites_data, batch_data


def main():
    PUBLIC_DIR.mkdir(exist_ok=True)
    HEATMAPS_DIR.mkdir(exist_ok=True)

    print("\n=== Exporting web assets ===")
    print(f"  Target: {PUBLIC_DIR}")

    # ── 500 m primary ───────────────────────────────────────────────────────
    sites_data, batch_data = export_size(500)
    batch_data.sort(key=lambda x: x["composite"], reverse=True)

    renovation_data = {
        "generated": str(date.today()),
        "sites":     sites_data,
        "batch":     batch_data,
    }
    with open(PUBLIC_DIR / "renovation_data.json", "w") as f:
        json.dump(renovation_data, f, indent=2)
    print(f"\n  Wrote renovation_data.json")
    print(f"    {len(sites_data)} main sites, {len(batch_data)} batch courtyards")

    # ── 1 km extended ───────────────────────────────────────────────────────
    sites_1km, _ = export_size(1000)
    if sites_1km:
        renovation_1km = {
            "generated": str(date.today()),
            "sites":     sites_1km,
            "batch":     [],
        }
        with open(PUBLIC_DIR / "renovation_data_1km.json", "w") as f:
            json.dump(renovation_1km, f, indent=2)
        print(f"  Wrote renovation_data_1km.json  ({len(sites_1km)} sites)")

    # ── Auto-generate financial_data.json (500 m) ───────────────────────────
    try:
        from generate_financial_data import generate
        fin = generate(size=500)
        with open(PUBLIC_DIR / "financial_data.json", "w", encoding="utf-8") as fh:
            json.dump(fin, fh, indent=2)
        print(f"\n  Wrote financial_data.json ({len(fin)} sites)")
    except Exception as exc:
        print(f"\n  [warn] financial_data.json not updated: {exc}")

    # ── financial_data_1km.json ─────────────────────────────────────────────
    try:
        from generate_financial_data import generate
        fin1km = generate(size=1000)
        if fin1km:
            with open(PUBLIC_DIR / "financial_data_1km.json", "w", encoding="utf-8") as fh:
                json.dump(fin1km, fh, indent=2)
            print(f"  Wrote financial_data_1km.json ({len(fin1km)} sites)")
    except Exception as exc:
        print(f"\n  [warn] financial_data_1km.json not updated: {exc}")

    print(f"\n  To rebuild the map run:")
    print(f"    npm run dev   (inside {ANALYSIS_DIR.parent})")


if __name__ == "__main__":
    main()
