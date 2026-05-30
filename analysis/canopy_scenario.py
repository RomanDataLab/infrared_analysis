"""
RenovationMap -- Canopy shade structure scenario (hot sites)
============================================================
Adds a 200 × 200 m flat-roof canopy (3.5–4.5 m height) centred on the
analysis polygon and re-runs UTCI + wind.

Usage:
    python canopy_scenario.py --site riyadh
    python canopy_scenario.py --site mecca

Output: results/<site>/scenario_D_*.png + scenarios_summary.json updated
"""

import argparse, json, ssl, time, certifi
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
    WindModelRequest, UtciModelRequest, UtciModelBaseRequest, AnalysesName,
)
from infrared_sdk.buildings.types import DotBimMesh
from infrared_sdk.models import TimePeriod, Location
from sites import SITES

VALID_MATERIALS = {"asphalt", "concrete", "soil", "vegetation", "water"}
HOT_SITES = [k for k, v in SITES.items() if v["climate"] == "hot"]


# ---------------------------------------------------------------------------
# Canopy mesh builder
# ---------------------------------------------------------------------------

def canopy_mesh(cx=250.0, cy=250.0, size=200.0, h_bottom=3.5, h_top=4.5):
    """
    DotBimMesh: a flat-roof box (shade pergola) in polygon-bbox-SW local metres.
    Coordinates are relative to the SW corner of the analysis polygon bounding box.
    cx, cy  = centre of canopy in local metres (250, 250 = centre of 500 m zone)
    size    = side length in metres
    """
    x0, x1 = cx - size / 2, cx + size / 2
    y0, y1 = cy - size / 2, cy + size / 2

    coords = [
        x0, y0, h_bottom,   # 0 SW bottom
        x1, y0, h_bottom,   # 1 SE bottom
        x1, y1, h_bottom,   # 2 NE bottom
        x0, y1, h_bottom,   # 3 NW bottom
        x0, y0, h_top,      # 4 SW top
        x1, y0, h_top,      # 5 SE top
        x1, y1, h_top,      # 6 NE top
        x0, y1, h_top,      # 7 NW top
    ]

    indices = [
        0, 2, 1,  0, 3, 2,   # bottom face
        4, 5, 6,  4, 6, 7,   # top face (blocks sun)
        0, 1, 5,  0, 5, 4,   # front (y=y0)
        2, 3, 7,  2, 7, 6,   # back  (y=y1)
        3, 0, 4,  3, 4, 7,   # left  (x=x0)
        1, 2, 6,  1, 6, 5,   # right (x=x1)
    ]

    return {"canopy_001": DotBimMesh(mesh_id=99001, coordinates=coords, indices=indices)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fetched(out_dir):
    with open(out_dir / "fetched_data.json") as f:
        d = json.load(f)
    buildings = {k: DotBimMesh(**v) for k, v in d["buildings"].items()}
    veg_raw   = d["vegetation"]
    # Mirror the sparse-vegetation threshold from baseline.py
    vegetation = veg_raw if (veg_raw and len(veg_raw) >= 10) else None

    # Use NDVI-derived trees if available (keeps scenario D consistent with baseline)
    ndvi_path = out_dir / "ndvi_trees.json"
    if ndvi_path.exists():
        try:
            with open(ndvi_path) as _f:
                ndvi_trees = json.load(_f)
            if ndvi_trees and len(ndvi_trees) >= 10:
                vegetation = ndvi_trees
        except Exception:
            pass

    gm = {k: v for k, v in d["ground_materials"].items() if k in VALID_MATERIALS}
    return buildings, vegetation, gm


def legend_bounds(r, g):
    lo = r.min_legend if r.min_legend is not None else float(np.nanmin(g))
    hi = r.max_legend if r.max_legend is not None else float(np.nanmax(g))
    return lo, hi


def _save_overlay_png(grid, path, cmap_name, vmin, vmax):
    cmap_obj = colormaps[cmap_name].copy()
    cmap_obj.set_bad(alpha=0)
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = cmap_obj(norm(np.flipud(grid)))
    _PILImage.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(path)


def save_heatmap(grid, title, path, cmap, lo, hi, unit=""):
    path = Path(path)
    fig = plt.figure(figsize=(5.5, 6.0), facecolor="white")
    gs  = fig.add_gridspec(
        2, 1, height_ratios=[1, 0.065],
        top=0.89, bottom=0.04, left=0.03, right=0.97, hspace=0.15,
    )
    ax  = fig.add_subplot(gs[0])
    cax = fig.add_subplot(gs[1])

    im = ax.imshow(np.where(np.isnan(grid), np.nan, grid),
                   cmap=cmap, origin="lower", vmin=lo, vmax=hi,
                   interpolation="nearest")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=7, linespacing=1.35)
    ax.axis("off")

    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    if unit:
        cb.set_label(unit, fontsize=11, labelpad=5)
    cb.ax.tick_params(labelsize=9)

    fig.savefig(path, dpi=130)
    plt.close(fig)
    _save_overlay_png(grid, path.parent / (path.stem + "_overlay.png"), cmap, lo, hi)
    print(f"   ok  {path.name}")


def save_delta(delta, title, path, label="improvement (green=better)"):
    valid = delta[~np.isnan(delta)]
    if not len(valid):
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
                   cmap="RdYlGn", origin="lower", vmin=-vabs, vmax=vabs,
                   interpolation="nearest")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=7, linespacing=1.35)
    ax.axis("off")

    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label(label, fontsize=10, labelpad=5)
    cb.ax.tick_params(labelsize=9)

    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"   ok  {Path(path).name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(site_key):
    site    = SITES[site_key]
    out     = Path(__file__).parent / "results" / site_key
    polygon = site["polygon"]
    um      = site["utci_month"]
    uh_s, uh_e = site["utci_hours"]
    days_in_month = {1:31,2:28,3:31,4:30,5:31,6:30,
                     7:31,8:31,9:30,10:31,11:30,12:31}

    tp_utci = TimePeriod(start_month=um, start_day=1, start_hour=uh_s,
                         end_month=um, end_day=days_in_month[um], end_hour=uh_e)
    loc = Location(latitude=site["lat"], longitude=site["lon"])

    base_wind = np.load(out / "baseline_wind.npy")
    base_utci = np.load(out / "baseline_utci.npy")

    print(f"\n=== Canopy Scenario D: {site['name']} ===")
    buildings, vegetation, gm = load_fetched(out)

    # Add 200 × 200 m canopy at centre of analysis zone
    canopy = canopy_mesh(cx=500.0, cy=500.0, size=200.0)
    buildings_with_canopy = {**buildings, **canopy}
    print(f"   Canopy: 200×200 m at 3.5–4.5 m height, centred on polygon")
    print(f"   Buildings (incl. canopy): {len(buildings_with_canopy)}")

    with InfraredClient() as client:
        stations = client.weather.get_weather_file_from_location(
            lat=site["lat"], lon=site["lon"], radius=site["weather_radius"]
        )
        weather = client.weather.filter_weather_data(
            identifier=stations[0]["uuid"], time_period=tp_utci
        )

        # -- Wind with canopy ------------------------------------------------
        print("\n[D] Wind (canopy added)...")
        schedule = client.run_area(
            WindModelRequest(analysis_type=AnalysesName.wind_speed,
                             wind_speed=site["wind_speed"],
                             wind_direction=site["wind_direction"]),
            polygon, buildings=buildings_with_canopy,
        )
        time.sleep(4)
        while True:
            st = client.check_area_state(schedule)
            if st.running == 0 and (st.succeeded + st.failed) >= len(schedule.jobs):
                break
            time.sleep(8)
        r_d_wind = client.merge_area_jobs(
            schedule, strategy="directional_blend",
            wind_direction_deg=float(site["wind_direction"]),
        )
        np.save(out / "scenario_D_wind.npy", r_d_wind.merged_grid)
        lo, hi = legend_bounds(r_d_wind, r_d_wind.merged_grid)
        save_heatmap(r_d_wind.merged_grid,
                     f"Scenario D Wind — 200m canopy\n{site['name']}",
                     out / "scenario_D_wind.png", "YlOrRd", lo, hi, "m/s")
        # hot: more wind = better (cooling) → delta = scen - base, green = +ve
        save_delta(r_d_wind.merged_grid - base_wind,
                   "Scenario D Wind delta — green = more wind = better cooling",
                   out / "scenario_D_delta_wind.png",
                   "wind change m/s (green=more wind=better cooling)")

        # -- UTCI with canopy ------------------------------------------------
        print("[D] UTCI (canopy added)...")
        r_d_utci = client.run_area_and_wait(
            UtciModelRequest.from_weatherfile_payload(
                payload=UtciModelBaseRequest(
                    analysis_type=AnalysesName.thermal_comfort_index,
                ),
                location=loc, time_period=tp_utci, weather_data=weather,
            ),
            polygon,
            buildings=buildings_with_canopy,
            vegetation=vegetation if vegetation else None,
            ground_materials=gm if gm else None,
        )
        np.save(out / "scenario_D_utci.npy", r_d_utci.merged_grid)
        lo, hi = legend_bounds(r_d_utci, r_d_utci.merged_grid)
        save_heatmap(r_d_utci.merged_grid,
                     f"Scenario D UTCI — 200m canopy\n{site['name']}",
                     out / "scenario_D_utci.png", "RdYlBu_r", lo, hi, "UTCI deg C")
        # hot: cooler = better → delta = base - scen, green = +ve
        save_delta(base_utci - r_d_utci.merged_grid,
                   "Scenario D UTCI delta — green = cooler = better",
                   out / "scenario_D_delta_utci.png",
                   "UTCI improvement degC (green=cooler=better)")

    # -- Stats ---------------------------------------------------------------
    dw = r_d_wind.merged_grid - base_wind   # +ve = more wind (cooling)
    du = base_utci - r_d_utci.merged_grid   # +ve = cooler (better)
    vw = ~np.isnan(dw)
    vu = ~np.isnan(du)

    d_stats = {
        "label":              "200m canopy shade structure",
        "wind_delta_raw":     round(float(dw[vw].mean()), 3),
        "utci_delta_raw":     round(float((-du)[vu].mean()), 3),
        "wind_improvement":   round(float(dw[vw].mean()), 3),
        "utci_improvement":   round(float(du[vu].mean()), 3),
        "frac_wind_improved": round(float((dw[vw] > 0.1).mean()), 3),
        "frac_utci_improved": round(float((du[vu] > 0.5).mean()), 3),
    }

    # Append/update scenarios_summary.json
    summary_path = out / "scenarios_summary.json"
    summary = {}
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
    summary["D"] = d_stats
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n--- CANOPY RESULT: {site['name']} ---")
    print(f"  Wind change:      {d_stats['wind_improvement']:+.3f} m/s mean  "
          f"({d_stats['frac_wind_improved']*100:.0f}% cells)")
    print(f"  UTCI improvement: {d_stats['utci_improvement']:+.3f} degC mean  "
          f"({d_stats['frac_utci_improved']*100:.0f}% cells)")
    print(f"  Baseline UTCI:  {np.nanmean(base_utci):.2f} degC")
    print(f"  Canopy   UTCI:  {np.nanmean(r_d_utci.merged_grid):.2f} degC")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run canopy shade structure scenario (Scenario D) for a hot site"
    )
    parser.add_argument(
        "--site", required=True, choices=HOT_SITES,
        help=f"Hot site to analyse: {HOT_SITES}"
    )
    args = parser.parse_args()
    main(args.site)
