"""
RenovationMap -- Track B: Batch district triage
================================================
Slices the 512x512 baseline grids into 5 sub-courtyards (~165x165 m each,
a quincunx layout covering the full 500x500 m study area) and scores each
independently -- no extra API calls needed.

Usage:
    python batch.py                  # score both sites
    python batch.py --site almaty
    python batch.py --site riyadh

Output:
    results/<site>/batch_results.json    one file per site
    results/batch_combined.json          both sites merged, ranked by score
"""

import argparse, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from sites import SITES

# ---------------------------------------------------------------------------
# 5 sub-patch definitions in 512x512 pixel space (quincunx pattern)
# Each patch is ~171x171 px = ~167x167 m at 500/512 m/px
# ---------------------------------------------------------------------------
PATCHES = [
    {"id": "NW",  "label": "NW Courtyard",     "rows": (0,   171), "cols": (0,   171)},
    {"id": "NE",  "label": "NE Courtyard",     "rows": (0,   171), "cols": (341, 512)},
    {"id": "CTR", "label": "Central Courtyard","rows": (171, 341), "cols": (171, 341)},
    {"id": "SW",  "label": "SW Courtyard",     "rows": (341, 512), "cols": (0,   171)},
    {"id": "SE",  "label": "SE Courtyard",     "rows": (341, 512), "cols": (341, 512)},
]

M_PER_PX = 500.0 / 512.0   # ~0.977 m per pixel

GRADE_LETTERS = [
    (80, "F"), (65, "E"), (50, "D"),
    (35, "C"), (20, "B"), (0,  "A"),
]
GRADE_FULL = {
    "F": "F  Critical   -- fix immediately",
    "E": "E  Severe     -- high renovation priority",
    "D": "D  Poor       -- include in next cycle",
    "C": "C  Moderate   -- improvements recommended",
    "B": "B  Fair       -- minor enhancements worthwhile",
    "A": "A  Good       -- no urgent intervention needed",
}
GRADE_COLORS = {
    "F": "#d32f2f", "E": "#f57c00", "D": "#fbc02d",
    "C": "#8bc34a", "B": "#4caf50", "A": "#2e7d32",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pixel_to_latlon(site_lat, site_lon, row_c, col_c):
    """
    Convert pixel-centre (row, col) in the 512x512 grid to WGS84 lat/lon.
    Grid convention: row 0 = south edge, col 0 = west edge (SDK spec).
    Local frame: SW = origin, y increases north, x increases east.
    """
    y_m = row_c * M_PER_PX                  # metres north of SW corner
    x_m = col_c * M_PER_PX                  # metres east of SW corner
    dy_m = y_m - 250.0                       # offset from centre
    dx_m = x_m - 250.0
    lat = site_lat + dy_m / 111320.0
    lon = site_lon + dx_m / (111320.0 * math.cos(math.radians(site_lat)))
    return round(lat, 6), round(lon, 6)


def normalise(value, worst, best):
    if worst == best:
        return 0.0
    return max(0.0, min(1.0, (value - best) / (worst - best)))


def grade_letter(score):
    for threshold, letter in GRADE_LETTERS:
        if score >= threshold:
            return letter
    return "A"


def patch_stats(wind_arr, sun_arr, utci_arr, sc):
    """Compute normalised score components for one patch sub-array."""

    vw = ~np.isnan(wind_arr)
    if vw.any():
        wm = sc["wind_metric"]
        if   wm == "frac_gt5ms":  w_val = float((wind_arr[vw] > 5).mean())
        elif wm == "frac_lt1ms":  w_val = float((wind_arr[vw] < 1).mean())
        else:                      w_val = float(wind_arr[vw].mean())
    else:
        w_val = 0.0

    vs = ~np.isnan(sun_arr)
    if vs.any():
        sm = sc["solar_metric"]
        if   sm == "frac_lt1h":   s_val = float((sun_arr[vs] < 1).mean())
        elif sm == "frac_gt5h":   s_val = float((sun_arr[vs] > 5).mean())
        else:                      s_val = float(sun_arr[vs].mean())
    else:
        s_val = 0.0

    vu = ~np.isnan(utci_arr)
    if vu.any():
        thresh = sc["utci_thresh"]
        if sc["utci_bad_dir"] == "above":
            u_val = float((utci_arr[vu] > thresh).mean())
        else:
            u_val = float((utci_arr[vu] < thresh).mean())
    else:
        u_val = 0.0

    ws = normalise(w_val, sc["wind_worst"],  sc["wind_best"])
    ss = normalise(s_val, sc["solar_worst"], sc["solar_best"])
    us = normalise(u_val, sc["utci_worst"],  sc["utci_best"])

    composite = (
        sc["wind_weight"]  * ws +
        sc["solar_weight"] * ss +
        sc["utci_weight"]  * us
    ) * 100.0

    return {
        "composite":   round(composite, 1),
        "wind_score":  round(ws * 100, 1),
        "solar_score": round(ss * 100, 1),
        "utci_score":  round(us * 100, 1),
        "wind_val":    round(w_val, 3),
        "solar_val":   round(s_val, 3),
        "utci_val":    round(u_val, 3),
        # readable labels
        "wind_stat_label":  sc["wind_label"],
        "solar_stat_label": sc["solar_label"],
        "utci_stat_label":  sc["utci_label"],
    }


# ---------------------------------------------------------------------------
# Per-site triage
# ---------------------------------------------------------------------------

def triage_site(site_key):
    site = SITES[site_key]
    out  = Path(__file__).parent / "results" / site_key
    sc   = site["score_config"]

    wind_grid = np.load(out / "baseline_wind.npy")
    sun_grid  = np.load(out / "baseline_sun.npy")
    utci_grid = np.load(out / "baseline_utci.npy")

    results = []
    for p in PATCHES:
        rs, re = p["rows"]
        cs, ce = p["cols"]
        row_c = (rs + re - 1) / 2.0
        col_c = (cs + ce - 1) / 2.0
        lat, lon = pixel_to_latlon(site["lat"], site["lon"], row_c, col_c)

        scores = patch_stats(
            wind_grid[rs:re, cs:ce],
            sun_grid[rs:re, cs:ce],
            utci_grid[rs:re, cs:ce],
            sc,
        )
        g = grade_letter(scores["composite"])
        results.append({
            "site_key":    site_key,
            "site_name":   site["name"],
            "patch_id":    p["id"],
            "patch_label": p["label"],
            "lat":         lat,
            "lon":         lon,
            "grade_short": g,
            "grade":       GRADE_FULL[g],
            **scores,
        })

    # Sort worst-first
    results.sort(key=lambda x: x["composite"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    out_path = out / "batch_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  -> {out_path.name}  ({len(results)} courtyards)")
    return results


# ---------------------------------------------------------------------------
# Overview heatmap annotated with patch boundaries + grades
# ---------------------------------------------------------------------------

def save_overview(site_key, results_for_site):
    site = SITES[site_key]
    out  = Path(__file__).parent / "results" / site_key
    utci_grid = np.load(out / "baseline_utci.npy")

    fig = plt.figure(figsize=(5.5, 6.0), facecolor="white")
    gs  = fig.add_gridspec(
        2, 1, height_ratios=[1, 0.065],
        top=0.89, bottom=0.04, left=0.03, right=0.97, hspace=0.15,
    )
    ax  = fig.add_subplot(gs[0])
    cax = fig.add_subplot(gs[1])

    im = ax.imshow(utci_grid, cmap="RdYlBu_r", origin="lower",
                   interpolation="nearest")

    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label("UTCI °C", fontsize=11, labelpad=5)
    cb.ax.tick_params(labelsize=9)

    # Draw patch rectangles + grade labels
    res_map = {r["patch_id"]: r for r in results_for_site}
    for p in PATCHES:
        rs, re = p["rows"]
        cs, ce = p["cols"]
        r = res_map[p["id"]]
        color = GRADE_COLORS[r["grade_short"]]
        rect = mpatches.Rectangle(
            (cs, rs), ce - cs, re - rs,
            linewidth=2.5, edgecolor=color,
            facecolor=color, alpha=0.18,
        )
        ax.add_patch(rect)
        ax.text(
            (cs + ce) / 2, (rs + re) / 2,
            f"{r['grade_short']}\n{r['composite']:.0f}",
            ha="center", va="center",
            fontsize=13, fontweight="bold",
            color=color,
        )

    ax.set_title(
        f"Batch Triage — {site['name']}\n"
        f"5 sub-courtyards  ·  worst = red  ·  best = green",
        fontsize=13, fontweight="bold", pad=7, linespacing=1.35,
    )
    ax.axis("off")
    path = out / "batch_overview.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"  -> {path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()) + ["all"],
                        default="all")
    args = parser.parse_args()

    sites = list(SITES.keys()) if args.site == "all" else [args.site]

    all_results = []
    for sk in sites:
        print(f"\n[Batch triage] {SITES[sk]['name']}")
        res = triage_site(sk)
        save_overview(sk, res)
        all_results.extend(res)

        print(f"  Ranked courtyards:")
        for r in res:
            print(f"    #{r['rank']} [{r['grade_short']}] {r['patch_label']}  "
                  f"score={r['composite']:.1f}  "
                  f"utci_frac={r['utci_val']:.2%}")

    # Combined output (all sites, sorted by composite score)
    all_results.sort(key=lambda x: x["composite"], reverse=True)
    combined_path = Path(__file__).parent / "results" / "batch_combined.json"
    combined_path.parent.mkdir(exist_ok=True)
    with open(combined_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  -> {combined_path}  ({len(all_results)} total courtyards)")


if __name__ == "__main__":
    main()
