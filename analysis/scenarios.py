"""
RenovationMap -- Step 2: Intervention scenarios
================================================
Usage:
    python scenarios.py --site almaty
    python scenarios.py --site riyadh

Loads cached fetched_data.json from baseline, re-runs wind + UTCI for:

  Almaty (cold)              Riyadh (hot)
  A  Windbreak birch trees   A  Date palm shade grid
  B  Asphalt -> grass        B  Asphalt -> pale concrete
  C  A + B combined          C  A + B combined

Outputs -> results/<site>/
    scenario_{A|B|C}_wind.npy / .png
    scenario_{A|B|C}_utci.npy / .png
    scenario_{A|B|C}_delta_wind.png   (green = improvement)
    scenario_{A|B|C}_delta_utci.png
    scenarios_summary.json
"""

import argparse
import json
import ssl
import time
import certifi
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.colors import Normalize
from PIL import Image as _PILImage
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ssl.create_default_context = lambda *a, **kw: ssl.create_default_context(
    *a, cafile=certifi.where(),
    **{k: v for k, v in kw.items() if k != "cafile"},
)

from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import (
    WindModelRequest,
    UtciModelRequest,
    UtciModelBaseRequest,
    AnalysesName,
)
from infrared_sdk.buildings.types import DotBimMesh
from infrared_sdk.models import TimePeriod, Location
from sites import SITES

VALID_MATERIALS = {"asphalt", "concrete", "soil", "vegetation", "water"}

days_in_month = {1:31,2:28,3:31,4:30,5:31,6:30,
                 7:31,8:31,9:30,10:31,11:30,12:31}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def results_dir(site_key):
    d = Path(__file__).parent / "results" / site_key
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_fetched(out_dir):
    with open(out_dir / "fetched_data.json") as f:
        data = json.load(f)
    buildings = {k: DotBimMesh(**v) for k, v in data["buildings"].items()}
    veg_raw   = data["vegetation"]
    # Mirror the sparse-vegetation threshold used in baseline.py:
    # fewer than 10 OSM trees → pass None so the API uses its own internal data,
    # exactly as the baseline simulation did.  Using the sparse list here but None
    # in the baseline would create an uncontrolled variable in the delta maps.
    vegetation = veg_raw if (veg_raw and len(veg_raw) >= 10) else None

    # If NDVI-derived trees exist (from postprocess_ndvi.py), use them instead.
    # This keeps scenario delta maps consistent with the enriched baseline.
    ndvi_path = out_dir / "ndvi_trees.json"
    if ndvi_path.exists():
        try:
            with open(ndvi_path) as _f:
                ndvi_trees = json.load(_f)
            if ndvi_trees and len(ndvi_trees) >= 10:
                vegetation = ndvi_trees
        except Exception:
            pass  # silently fall back to OSM veg

    ground_materials = {k: v for k, v in data["ground_materials"].items()
                        if k in VALID_MATERIALS}
    return buildings, vegetation, ground_materials


def legend_bounds(result, grid):
    lo = result.min_legend if result.min_legend is not None else float(np.nanmin(grid))
    hi = result.max_legend if result.max_legend is not None else float(np.nanmax(grid))
    return lo, hi


def _save_overlay_png(grid, path, cmap_name, vmin, vmax):
    cmap_obj = colormaps[cmap_name].copy()
    cmap_obj.set_bad(alpha=0)
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = cmap_obj(norm(np.flipud(grid)))
    _PILImage.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(path)


def save_heatmap(grid, title, path, cmap, vmin, vmax, unit=""):
    path = Path(path)
    fig = plt.figure(figsize=(5.5, 6.0), facecolor="white")
    gs  = fig.add_gridspec(
        2, 1, height_ratios=[1, 0.065],
        top=0.89, bottom=0.04, left=0.03, right=0.97, hspace=0.15,
    )
    ax  = fig.add_subplot(gs[0])
    cax = fig.add_subplot(gs[1])

    im = ax.imshow(np.where(np.isnan(grid), np.nan, grid),
                   cmap=cmap, origin="lower", vmin=vmin, vmax=vmax,
                   interpolation="nearest")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=7, linespacing=1.35)
    ax.axis("off")

    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    if unit:
        cb.set_label(unit, fontsize=11, labelpad=5)
    cb.ax.tick_params(labelsize=9)

    fig.savefig(path, dpi=130)
    plt.close(fig)
    _save_overlay_png(grid, path.parent / (path.stem + "_overlay.png"), cmap, vmin, vmax)
    print(f"   ok  {path.name}")


def save_delta(delta, title, path, label="baseline - scenario"):
    """
    Almaty (cold): positive delta wind = less wind = good (green)
                   positive delta UTCI = warmer feels = good (green)
    Riyadh (hot):  positive delta wind = less wind = NOT good (less cooling)
                   positive delta UTCI = hotter = bad
    We always show green = improvement in context — caller passes the right sign.
    """
    valid = delta[~np.isnan(delta)]
    if len(valid) == 0:
        return
    vabs = max(np.percentile(np.abs(valid), 95), 0.01)

    fig = plt.figure(figsize=(5.5, 6.0), facecolor="white")
    gs  = fig.add_gridspec(
        2, 1, height_ratios=[1, 0.065],
        top=0.89, bottom=0.04, left=0.03, right=0.97, hspace=0.15,
    )
    ax  = fig.add_subplot(gs[0])
    cax = fig.add_subplot(gs[1])

    im = ax.imshow(np.where(np.isnan(delta), np.nan, delta),
                   cmap="RdYlGn", origin="lower",
                   vmin=-vabs, vmax=vabs, interpolation="nearest")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=7, linespacing=1.35)
    ax.axis("off")

    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label(label, fontsize=10, labelpad=5)
    cb.ax.tick_params(labelsize=9)

    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"   ok  {Path(path).name}")


def run_wind(client, site, polygon, buildings, vegetation):
    """Run wind and return AreaResult using directional_blend."""
    schedule = client.run_area(
        WindModelRequest(
            analysis_type=AnalysesName.wind_speed,
            wind_speed=site["wind_speed"],
            wind_direction=site["wind_direction"],
        ),
        polygon,
        buildings=buildings,
        vegetation=vegetation if vegetation else None,
    )
    time.sleep(4)
    while True:
        st = client.check_area_state(schedule)
        if st.running == 0 and (st.succeeded + st.failed) >= len(schedule.jobs):
            break
        time.sleep(8)
    return client.merge_area_jobs(
        schedule, strategy="directional_blend",
        wind_direction_deg=float(site["wind_direction"]),
    )


def run_utci(client, site, polygon, buildings, vegetation, ground_materials, weather, tp_utci):
    return client.run_area_and_wait(
        UtciModelRequest.from_weatherfile_payload(
            payload=UtciModelBaseRequest(
                analysis_type=AnalysesName.thermal_comfort_index,
            ),
            location=Location(latitude=site["lat"], longitude=site["lon"]),
            time_period=tp_utci,
            weather_data=weather,
        ),
        polygon,
        buildings=buildings,
        vegetation=vegetation if vegetation else None,
        ground_materials=ground_materials if ground_materials else None,
    )


def scenario_stats(label, base_wind, scen_wind, base_utci, scen_utci, climate):
    """
    delta = base - scen
    cold climate: positive delta wind = good (less wind), positive delta UTCI = good (warmer)
    hot  climate: positive delta wind = neutral (less Shamal cooling)
                  NEGATIVE delta UTCI = good (cooler)
    We report raw delta and compute improvement fraction per-climate.
    """
    dw = base_wind - scen_wind
    du = base_utci - scen_utci
    vw = ~np.isnan(dw)
    vu = ~np.isnan(du)

    if climate == "cold":
        # improvement = less wind (dw>0) or warmer UTCI (du>0 means scen is cooler = bad)
        # Actually: for cold, warmer is better, so we want scen_utci > base_utci → du < 0
        # frac improved wind: scen_wind < base_wind → dw > 0.1
        # frac improved utci: scen_utci > base_utci → du < -0.5
        frac_wind_ok  = float((dw[vw] > 0.10).mean())
        frac_utci_ok  = float((du[vu] < -0.50).mean())   # scen warmer = du negative
        wind_imp_sign = float(dw[vw].mean())              # +ve = less wind
        utci_imp_sign = -float(du[vu].mean())             # +ve = scen is warmer
    else:
        # hot: improved wind = more wind (dw < 0 → scen windier = cooling benefit)
        #      improved UTCI = scen cooler → du > 0 (base > scen)
        frac_wind_ok  = float((dw[vw] < -0.10).mean())   # scen windier = cooling
        frac_utci_ok  = float((du[vu] >  0.50).mean())   # scen cooler
        wind_imp_sign = -float(dw[vw].mean())             # +ve = scen windier
        utci_imp_sign = float(du[vu].mean())              # +ve = scen cooler

    return {
        "label":                label,
        "wind_delta_raw":       round(float(dw[vw].mean()), 3),
        "utci_delta_raw":       round(float(du[vu].mean()), 3),
        "wind_improvement":     round(wind_imp_sign, 3),
        "utci_improvement":     round(utci_imp_sign, 3),
        "frac_wind_improved":   round(frac_wind_ok,  3),
        "frac_utci_improved":   round(frac_utci_ok,  3),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(site_key):
    site    = SITES[site_key]
    out     = results_dir(site_key)
    climate = site["climate"]
    polygon = site["polygon"]
    um      = site["utci_month"]
    uh_s, uh_e = site["utci_hours"]

    tp_utci = TimePeriod(
        start_month=um, start_day=1,  start_hour=uh_s,
        end_month=um,   end_day=days_in_month[um], end_hour=uh_e,
    )

    print(f"\n=== Scenarios: {site['name']} ===")

    base_wind = np.load(out / "baseline_wind.npy")
    base_utci = np.load(out / "baseline_utci.npy")

    print("Loading cached fetched data...")
    buildings, vegetation, ground_materials = load_fetched(out)

    summary = {}

    utci_cmap = "RdYlBu_r" if climate == "hot" else "RdYlBu"

    with InfraredClient() as client:
        stations = client.weather.get_weather_file_from_location(
            lat=site["lat"], lon=site["lon"], radius=site["weather_radius"]
        )
        weather = client.weather.filter_weather_data(
            identifier=stations[0]["uuid"], time_period=tp_utci
        )

        # ---- Scenario A -------------------------------------------------
        scfg_a = site["scenario_A"]
        print(f"\n-- Scenario A: {scfg_a['label']} --")

        trees_a = scfg_a["tree_fn"]() if scfg_a["tree_fn"] else {}
        # Merge intervention trees on top of the baseline vegetation (None for sparse sites).
        # {**(None→{}) + trees_a} or None  — preserves falsy→None so run_wind/run_utci
        # get None when there are genuinely no trees to pass.
        veg_a = ({**(vegetation or {}), **trees_a}) or None

        print("   wind...")
        r_a_wind = run_wind(client, site, polygon, buildings, veg_a)
        np.save(out / "scenario_A_wind.npy", r_a_wind.merged_grid)
        lo, hi = legend_bounds(r_a_wind, r_a_wind.merged_grid)
        save_heatmap(r_a_wind.merged_grid, f"Scenario A Wind — {scfg_a['label']}",
                     out / "scenario_A_wind.png", "YlOrRd", lo, hi, "m/s")

        # delta: for cold, green = less wind; for hot, green = more wind (cooling)
        delta_wind_a = (base_wind - r_a_wind.merged_grid) if climate == "cold" \
                       else (r_a_wind.merged_grid - base_wind)
        save_delta(delta_wind_a,
                   f"Scenario A Wind delta — green = {'less' if climate=='cold' else 'more'} wind",
                   out / "scenario_A_delta_wind.png",
                   label="wind improvement (m/s, green=better)")

        print("   utci...")
        r_a_utci = run_utci(client, site, polygon, buildings, veg_a,
                             ground_materials, weather, tp_utci)
        np.save(out / "scenario_A_utci.npy", r_a_utci.merged_grid)
        lo, hi = legend_bounds(r_a_utci, r_a_utci.merged_grid)
        save_heatmap(r_a_utci.merged_grid, f"Scenario A UTCI — {scfg_a['label']}",
                     out / "scenario_A_utci.png", utci_cmap, lo, hi, "UTCI deg C")

        # delta: green = warmer (cold) or cooler (hot)
        delta_utci_a = (r_a_utci.merged_grid - base_utci) if climate == "cold" \
                       else (base_utci - r_a_utci.merged_grid)
        save_delta(delta_utci_a,
                   f"Scenario A UTCI delta — green = {'warmer' if climate=='cold' else 'cooler'}",
                   out / "scenario_A_delta_utci.png",
                   label="UTCI improvement (degC, green=better)")

        summary["A"] = scenario_stats(scfg_a["label"],
                                       base_wind, r_a_wind.merged_grid,
                                       base_utci, r_a_utci.merged_grid, climate)
        print(f"   wind improv: {summary['A']['wind_improvement']:+.3f} m/s | "
              f"utci improv: {summary['A']['utci_improvement']:+.3f} degC")

        # ---- Scenario B -------------------------------------------------
        scfg_b = site["scenario_B"]
        print(f"\n-- Scenario B: {scfg_b['label']} --")

        gm_b = dict(ground_materials)
        if scfg_b["ground_key"]:
            gm_b[scfg_b["ground_key"]] = scfg_b["ground_fc"]

        # Wind unaffected by ground material — reuse baseline for B wind
        print("   utci (ground change only — wind stays at baseline)...")
        r_b_utci = run_utci(client, site, polygon, buildings, vegetation,
                             gm_b, weather, tp_utci)
        np.save(out / "scenario_B_utci.npy", r_b_utci.merged_grid)
        lo, hi = legend_bounds(r_b_utci, r_b_utci.merged_grid)
        save_heatmap(r_b_utci.merged_grid, f"Scenario B UTCI — {scfg_b['label']}",
                     out / "scenario_B_utci.png", utci_cmap, lo, hi, "UTCI deg C")

        delta_utci_b = (r_b_utci.merged_grid - base_utci) if climate == "cold" \
                       else (base_utci - r_b_utci.merged_grid)
        save_delta(delta_utci_b,
                   f"Scenario B UTCI delta — green = {'warmer' if climate=='cold' else 'cooler'}",
                   out / "scenario_B_delta_utci.png",
                   label="UTCI improvement (degC, green=better)")

        summary["B"] = scenario_stats(scfg_b["label"],
                                       base_wind, base_wind,
                                       base_utci, r_b_utci.merged_grid, climate)
        print(f"   utci improv: {summary['B']['utci_improvement']:+.3f} degC")

        # ---- Scenario C (A + B) ----------------------------------------
        label_c = site["scenario_C_label"]
        print(f"\n-- Scenario C: {label_c} --")

        print("   wind...")
        r_c_wind = run_wind(client, site, polygon, buildings, veg_a)
        np.save(out / "scenario_C_wind.npy", r_c_wind.merged_grid)
        lo, hi = legend_bounds(r_c_wind, r_c_wind.merged_grid)
        save_heatmap(r_c_wind.merged_grid, f"Scenario C Wind — {label_c}",
                     out / "scenario_C_wind.png", "YlOrRd", lo, hi, "m/s")

        delta_wind_c = (base_wind - r_c_wind.merged_grid) if climate == "cold" \
                       else (r_c_wind.merged_grid - base_wind)
        save_delta(delta_wind_c,
                   f"Scenario C Wind delta — green = better",
                   out / "scenario_C_delta_wind.png",
                   label="wind improvement (m/s, green=better)")

        print("   utci...")
        r_c_utci = run_utci(client, site, polygon, buildings, veg_a,
                             gm_b, weather, tp_utci)
        np.save(out / "scenario_C_utci.npy", r_c_utci.merged_grid)
        lo, hi = legend_bounds(r_c_utci, r_c_utci.merged_grid)
        save_heatmap(r_c_utci.merged_grid, f"Scenario C UTCI — {label_c}",
                     out / "scenario_C_utci.png", utci_cmap, lo, hi, "UTCI deg C")

        delta_utci_c = (r_c_utci.merged_grid - base_utci) if climate == "cold" \
                       else (base_utci - r_c_utci.merged_grid)
        save_delta(delta_utci_c,
                   f"Scenario C UTCI delta — green = better",
                   out / "scenario_C_delta_utci.png",
                   label="UTCI improvement (degC, green=better)")

        summary["C"] = scenario_stats(label_c,
                                       base_wind, r_c_wind.merged_grid,
                                       base_utci, r_c_utci.merged_grid, climate)
        print(f"   wind improv: {summary['C']['wind_improvement']:+.3f} m/s | "
              f"utci improv: {summary['C']['utci_improvement']:+.3f} degC")

    with open(out / "scenarios_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n--- SCENARIOS COMPLETE: {site['name']} ---")
    for k, s in summary.items():
        print(f"  [{k}] {s['label']}")
        print(f"       wind improv {s['wind_improvement']:+.3f} m/s  "
              f"({s['frac_wind_improved']*100:.0f}% cells)")
        print(f"       utci improv {s['utci_improvement']:+.3f} degC  "
              f"({s['frac_utci_improved']*100:.0f}% cells)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()), required=True)
    args = parser.parse_args()
    main(args.site)
