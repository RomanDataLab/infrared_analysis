"""
RenovationMap -- Step 1: Baseline courtyard analysis
=====================================================
Usage:
    python baseline.py --site almaty
    python baseline.py --site riyadh

Runs three analyses per site:
  * wind-speed          -- prevailing seasonal wind
  * direct-sun-hours    -- worst-case solar month (geometry-only)
  * UTCI                -- worst-case thermal comfort month

Outputs -> analysis/results/<site>/
    baseline_wind.npy / .png
    baseline_sun.npy  / .png   (normalised to hrs/day)
    baseline_utci.npy / .png
    baseline_stats.json
    fetched_data.json           (cached for scenarios.py)
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
from scipy.ndimage import distance_transform_edt as _dtedt

load_dotenv(Path(__file__).parent.parent / ".env")

# Fix Windows SSL certificate chain
ssl.create_default_context = lambda *a, **kw: ssl.create_default_context(
    *a, cafile=certifi.where(),
    **{k: v for k, v in kw.items() if k != "cafile"},
)

from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import (
    WindModelRequest,
    SolarModelRequest,
    UtciModelRequest,
    UtciModelBaseRequest,
    AnalysesName,
)
from infrared_sdk.buildings.types import DotBimMesh
from infrared_sdk.models import TimePeriod, Location
from sites import SITES

VALID_MATERIALS = {"asphalt", "concrete", "soil", "vegetation", "water"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def results_dir(site_key, size=500):
    d = Path(__file__).parent / "results" / site_key
    if size == 1000:
        d = d / "1km"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fill_nan_nearest(grid):
    """Replace NaN cells with the nearest valid cell value (O(n))."""
    nan_mask = np.isnan(grid)
    if not nan_mask.any():
        return grid
    _, (ri, ci) = _dtedt(nan_mask, return_distances=True, return_indices=True)
    filled = grid.copy()
    filled[nan_mask] = grid[ri[nan_mask], ci[nan_mask]]
    return filled


def _save_overlay_png(grid, path, cmap_name, vmin, vmax, fill_nan=False):
    """Pure RGBA PNG for Leaflet imageOverlay — no axes, NaN = transparent.

    Flipped vertically so row 0 (south) ends up at the bottom of the file,
    matching Leaflet's convention (top of image = north).

    fill_nan : fill NaN corners with nearest-valid-neighbour so the overlay
               covers the full bounding box (use for wind grids whose CFD
               domain is circular and leaves rectangular corners empty).
    """
    cmap_obj = colormaps[cmap_name].copy()
    cmap_obj.set_bad(alpha=0)
    render = _fill_nan_nearest(grid) if fill_nan else grid
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = cmap_obj(norm(np.flipud(render)))
    _PILImage.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(path)


def save_heatmap(grid, title, path, cmap, vmin, vmax, unit="", fill_nan=False):
    """Save thumbnail PNG (title + map + horizontal colorbar) and a clean overlay PNG.

    fill_nan : passed through to _save_overlay_png — set True for wind grids
               so the NaN corners from the circular CFD domain get filled.
    """
    path = Path(path)
    # Square layout: map area + title on top, horizontal colorbar at bottom.
    # Proportions chosen so the image looks good both as a ~96 px thumbnail
    # and when opened full-size in the browser.
    fig = plt.figure(figsize=(5.5, 6.0), facecolor="white")
    gs  = fig.add_gridspec(
        2, 1, height_ratios=[1, 0.065],
        top=0.89, bottom=0.04, left=0.03, right=0.97, hspace=0.15,
    )
    ax  = fig.add_subplot(gs[0])
    cax = fig.add_subplot(gs[1])

    im = ax.imshow(
        np.where(np.isnan(grid), np.nan, grid),
        cmap=cmap, origin="lower", vmin=vmin, vmax=vmax,
        interpolation="nearest",
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=7, linespacing=1.35)
    ax.axis("off")

    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    if unit:
        cb.set_label(unit, fontsize=11, labelpad=5)
    cb.ax.tick_params(labelsize=9)

    fig.savefig(path, dpi=130)
    plt.close(fig)
    # Overlay PNG for Leaflet (pure grid, no decorations)
    _save_overlay_png(grid, path.parent / (path.stem + "_overlay.png"), cmap, vmin, vmax,
                      fill_nan=fill_nan)
    print(f"   ok  {path.name}")


def legend_bounds(result, grid):
    lo = result.min_legend if result.min_legend is not None else float(np.nanmin(grid))
    hi = result.max_legend if result.max_legend is not None else float(np.nanmax(grid))
    return lo, hi


def load_cached(out_dir):
    """Load buildings, vegetation, ground_materials, weather UUID from cached fetched_data.json."""
    with open(out_dir / "fetched_data.json") as f:
        data = json.load(f)
    buildings = {k: DotBimMesh(**v) for k, v in data["buildings"].items()}
    veg_raw = data["vegetation"]
    vegetation = veg_raw if (veg_raw and len(veg_raw) >= 10) else None
    ground_materials = {k: v for k, v in data["ground_materials"].items()
                        if k in VALID_MATERIALS}
    station_id = data.get("weather_station_uuid")
    return buildings, vegetation, ground_materials, station_id


def cache_fetched(out_dir, buildings, area_veg, layers, overture_checked: bool = False):
    """
    Persist fetched (and optionally Overture-enriched) data to fetched_data.json
    so that scenarios.py and canopy_scenario.py can load it without hitting the
    network again.

    buildings        : {id: DotBimMesh} — may include Overture additions
    overture_checked : True when enrich_buildings() was called regardless of
                       how many Overture buildings were added.  Stored so that
                       refine.py won't keep marking the site as stale when
                       Overture simply has no extra coverage for this bbox.
    """
    cache = {
        "buildings":        {k: v.model_dump() for k, v in buildings.items()},
        "vegetation":       area_veg.features,
        "ground_materials": layers,
        "overture_checked": overture_checked,
    }
    with open(out_dir / "fetched_data.json", "w") as f:
        json.dump(cache, f)
    print(f"   cached -> fetched_data.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(site_key, size=500, cached=False, buffer_m=None):
    site = SITES[site_key]
    out  = results_dir(site_key, size)

    polygon  = site["polygon"] if size == 500 else site["polygon_1km"]
    # Context polygon for building/vegetation fetch:
    #   --buffer 200 + --size 1000 -> use 1400m context polygon
    #   default 500m analysis -> 1500m context, 1km analysis -> 2000m context
    if buffer_m == 200 and size == 1000:
        ctx_poly = site.get("context_polygon_1km_200", site["context_polygon_1km"])
    elif size == 1000:
        ctx_poly = site.get("context_polygon_1km", site["context_polygon"])
    else:
        ctx_poly = site.get("context_polygon", polygon)
    loc      = Location(latitude=site["lat"], longitude=site["lon"])
    climate  = site["climate"]

    days_in_month = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30,
                     7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

    sh, eh   = site["solar_hours"]
    uh_s, uh_e = site["utci_hours"]
    sm       = site["solar_month"]
    um       = site["utci_month"]

    tp_solar = TimePeriod(start_month=sm, start_day=1,  start_hour=sh,
                          end_month=sm,   end_day=days_in_month[sm], end_hour=eh)
    tp_utci  = TimePeriod(start_month=um, start_day=1,  start_hour=uh_s,
                          end_month=um,   end_day=days_in_month[um], end_hour=uh_e)

    ctx_label = f"{int(size + 2 * (buffer_m or 500))} m" if buffer_m else ("1.5 km" if size == 500 else "2 km")
    print(f"\n=== {site['name']} ===")
    print(f"      analysis polygon : {size} m")
    print(f"      context polygon  : {ctx_label}  (buildings + vegetation fetch)")
    if cached:
        print(f"      mode             : CACHED (loading from fetched_data.json)")

    with InfraredClient() as client:

        if cached:
            # -- Load from cache (skip fetch steps 1-4) ----------------------
            print("\n[1-3/6] Loading cached data from fetched_data.json...")
            enriched_buildings, veg_for_sim, layers, station_id = load_cached(out)
            print(f"      {len(enriched_buildings)} buildings")
            print(f"      vegetation: {'yes' if veg_for_sim else 'None (sparse)'}")
            print(f"      ground layers: {list(layers.keys())}")
            print(f"      weather UUID: {station_id[:8] if station_id else 'None'}...")
        else:
            # -- Fetch context layers (from wider polygon) -------------------
            print(f"\n[1/6] Fetching buildings (context area {ctx_label})...")
            area = client.buildings.get_area(ctx_poly)
            n_fail = len(area.failed_tiles) if area.failed_tiles else 0
            print(f"      {len(area.buildings)} buildings (OSM)"
                  + (f"  ({n_fail} tiles failed)" if n_fail else ""))

            # Optional enrichment: add Overture Maps buildings not present in OSM.
            _overture_attempted = False
            try:
                from fetch_overture import enrich_buildings as _enrich
                enriched_buildings  = _enrich(site, area.buildings)
                _overture_attempted = True
            except ImportError:
                enriched_buildings = area.buildings

            print("[2/6] Fetching vegetation (context area)...")
            area_veg = client.vegetation.get_area(ctx_poly)
            n_trees  = len(area_veg.features)
            print(f"      {n_trees} trees (OSM)")
            veg_for_sim = area_veg.features if n_trees >= 10 else None
            if veg_for_sim is None and n_trees > 0:
                print(f"      (sparse -- {n_trees} trees below threshold; "
                      f"passing None so API uses its own vegetation data)")

            # Optional enrichment: NDVI-derived tree points
            ndvi_path = out / "ndvi_trees.json"
            if ndvi_path.exists():
                try:
                    with open(ndvi_path) as _f:
                        _ndvi = json.load(_f)
                    if _ndvi and len(_ndvi) >= 10:
                        veg_for_sim = _ndvi
                        print(f"      [ndvi] loaded {len(_ndvi)} canopy points "
                              f"from ndvi_trees.json (overrides OSM veg)")
                    else:
                        print(f"      [ndvi] ndvi_trees.json has < 10 features -- "
                              f"keeping OSM vegetation")
                except Exception as _e:
                    print(f"      [ndvi] could not load ndvi_trees.json: {_e}")

            print("[3/6] Fetching ground materials...")
            try:
                area_gm = client.ground_materials.get_area(polygon)
                layers  = {k: v for k, v in area_gm.layers.items() if k in VALID_MATERIALS}
                print(f"      layers: {list(layers.keys())}")
            except Exception as _gm_err:
                layers = {}
                print(f"      WARNING: ground material fetch failed ({_gm_err.__class__.__name__}: "
                      f"{str(_gm_err)[:120]})")
                print(f"      Continuing without ground materials -- API will use default surface.")

            cache_fetched(out, enriched_buildings, area_veg, layers,
                          overture_checked=_overture_attempted)

        # -- Weather station (non-fatal — UUID cached for later UTCI re-runs) --
        weather    = None
        if cached:
            print(f"[4/6] Weather station (cached UUID: {station_id[:8] if station_id else 'None'}...)")
        else:
            print("[4/6] Finding weather station...")
            station_id = None
        # Try to load cached UUID first (survives API downtime on re-runs)
        _fd_path = out / "fetched_data.json"
        if station_id is None and _fd_path.exists():
            try:
                with open(_fd_path) as _fd:
                    _fd_cache = json.load(_fd)
                station_id = _fd_cache.get("weather_station_uuid")
                if station_id:
                    print(f"      (loaded cached UUID: {station_id[:8]}...)")
            except Exception:
                pass
        if not cached:
            try:
                stations   = client.weather.get_weather_file_from_location(
                    lat=site["lat"], lon=site["lon"], radius=site["weather_radius"]
                )
                station_id = stations[0]["uuid"]
                print(f"      {stations[0]['fileName']}")
                # Persist UUID
                if _fd_path.exists():
                    try:
                        with open(_fd_path) as _fd:
                            _fd_cache = json.load(_fd)
                        _fd_cache["weather_station_uuid"] = station_id
                        with open(_fd_path, "w") as _fd:
                            json.dump(_fd_cache, _fd)
                    except Exception:
                        pass
            except Exception as _wx_err:
                print(f"      WARNING: weather station lookup failed ({_wx_err.__class__.__name__})")
                if station_id:
                    print(f"      Using cached UUID -- will retry filter_weather_data")
                else:
                    print(f"      No cached UUID -- UTCI will be skipped")

        if station_id is not None:
            try:
                weather = client.weather.filter_weather_data(
                    identifier=station_id, time_period=tp_utci
                )
            except Exception as _wf_err:
                print(f"      WARNING: filter_weather_data failed ({_wf_err.__class__.__name__})"
                      f" — UTCI will be skipped this run")

        # -- Analysis 1: Wind speed --------------------------------------
        wdir  = site["wind_direction"]
        wspd  = site["wind_speed"]
        print(f"\n[5a] Wind speed ({site['wind_label']})...")

        schedule = client.run_area(
            WindModelRequest(
                analysis_type=AnalysesName.wind_speed,
                wind_speed=wspd,
                wind_direction=wdir,
            ),
            polygon,
            buildings=enriched_buildings,
        )
        time.sleep(4)
        while True:
            st = client.check_area_state(schedule)
            if st.running == 0 and (st.succeeded + st.failed) >= len(schedule.jobs):
                break
            time.sleep(8)
        merge_strategy = site.get("wind_merge_strategy", "directional_blend")
        merge_kw = {"wind_direction_deg": float(wdir)} if merge_strategy != "default" else {}
        wind = client.merge_area_jobs(schedule, strategy=merge_strategy, **merge_kw)
        print(f"      merge strategy: {merge_strategy}")
        print(f"      grid {wind.grid_shape}  jobs {wind.succeeded_jobs}/{wind.total_jobs}")
        lo, hi = legend_bounds(wind, wind.merged_grid)
        save_heatmap(
            wind.merged_grid,
            f"{site['name']}\nWind Speed — {site['wind_label']}",
            out / "baseline_wind.png", "YlOrRd", lo, hi, "m/s",
            fill_nan=True,   # CFD domain is circular; fill NaN corners for full-rect overlay
        )
        np.save(out / "baseline_wind.npy", wind.merged_grid)

        # -- Analysis 2: Direct sun hours --------------------------------
        print(f"[5b] Direct sun hours (month {sm})...")
        sun = client.run_area_and_wait(
            SolarModelRequest(
                analysis_type=AnalysesName.direct_sun_hours,
                latitude=site["lat"],
                longitude=site["lon"],
                time_period=tp_solar,
            ),
            polygon,
            buildings=enriched_buildings,
        )
        print(f"      grid {sun.grid_shape}")
        days   = days_in_month[sm]
        per_day = sun.merged_grid / days
        lo, hi  = legend_bounds(sun, sun.merged_grid)
        cmap    = site["solar_cmap"]
        save_heatmap(
            per_day,
            f"{site['name']}\nDirect Sun Hours — month {sm} (hrs/day)",
            out / "baseline_sun.png", cmap,
            lo / days, hi / days, "hrs/day",
        )
        np.save(out / "baseline_sun.npy", sun.merged_grid)   # raw cumulative

        # -- Analysis 3: UTCI (skipped if weather unavailable) -----------
        utci = None
        if weather is not None:
            print(f"[5c] UTCI (month {um})...")
            utci = client.run_area_and_wait(
                UtciModelRequest.from_weatherfile_payload(
                    payload=UtciModelBaseRequest(
                        analysis_type=AnalysesName.thermal_comfort_index,
                    ),
                    location=loc,
                    time_period=tp_utci,
                    weather_data=weather,
                ),
                polygon,
                buildings=enriched_buildings,
                vegetation=veg_for_sim,
                ground_materials=layers,
            )
            print(f"      grid {utci.grid_shape}")
            lo, hi = legend_bounds(utci, utci.merged_grid)
            utci_cmap = "RdYlBu_r" if climate == "hot" else "RdYlBu"
            save_heatmap(
                utci.merged_grid,
                f"{site['name']}\nUTCI — month {um} (avg daytime, deg C)",
                out / "baseline_utci.png", utci_cmap, lo, hi, "UTCI deg C",
            )
            np.save(out / "baseline_utci.npy", utci.merged_grid)
        else:
            print(f"[5c] UTCI — SKIPPED (weather API unavailable)")

        # -- Save actual grid bounds from API (tile-snapped, may differ from polygon) --
        # AreaResult.bounds = (min_lng, min_lat, max_lng, max_lat) i.e. [W, S, E, N]
        # These are the TRUE geographic extents of the 512×512 grids.
        # We use UTCI bounds as the master; wind/sun should be identical for the
        # same polygon, but we save all three for verification.
        grid_bounds = {
            "wind": list(wind.bounds),
            "sun":  list(sun.bounds),
            "utci": list(utci.bounds) if utci is not None else None,
        }
        with open(out / "baseline_bounds.json", "w") as f:
            json.dump(grid_bounds, f, indent=2)
        master_bounds = utci.bounds if utci is not None else wind.bounds
        print(f"   bounds (W,S,E,N): {[round(x,6) for x in master_bounds]}")

        # -- Stats -------------------------------------------------------
        print("\n[6/6] Computing stats...")
        sc   = site["score_config"]
        w    = wind.merged_grid[~np.isnan(wind.merged_grid)]
        s    = per_day[~np.isnan(per_day)]
        thr  = sc["utci_thresh"]

        stats = {
            "site":    {"key": site_key, "name": site["name"],
                        "lat": site["lat"], "lon": site["lon"],
                        "polygon": polygon, "climate": climate},
            "wind": {
                "mean_ms":    round(float(w.mean()), 2),
                "max_ms":     round(float(w.max()),  2),
                "frac_gt5ms": round(float((w > 5).mean()), 3),
                "frac_lt1ms": round(float((w < 1).mean()), 3),
            },
            "sun": {
                "mean_hrs_day":  round(float(s.mean()), 2),
                "frac_lt1h":     round(float((s < 1).mean()), 3),
                "frac_gt5h":     round(float((s > 5).mean()), 3),
            },
            "utci": None,   # filled below if weather was available
        }

        if utci is not None:
            u = utci.merged_grid[~np.isnan(utci.merged_grid)]
            stats["utci"] = {
                "mean_c":        round(float(u.mean()), 2),
                "frac_utci_bad": round(float(
                    (u > thr).mean() if sc["utci_bad_dir"] == "above"
                    else (u < thr).mean()
                ), 3),
            }

        with open(out / "baseline_stats.json", "w") as f:
            json.dump(stats, f, indent=2)

        print(f"\n--- BASELINE: {site['name']} ---")
        if climate == "cold":
            print(f"  Wind  {stats['wind']['mean_ms']} m/s mean | "
                  f"{stats['wind']['frac_gt5ms']*100:.0f}% > 5 m/s")
            print(f"  Sun   {stats['sun']['mean_hrs_day']} h/day (Dec) | "
                  f"{stats['sun']['frac_lt1h']*100:.0f}% < 1 h/day")
            if stats["utci"]:
                print(f"  UTCI  {stats['utci']['mean_c']} deg C (Jan) | "
                      f"{stats['utci']['frac_utci_bad']*100:.0f}% cold stress (<{thr} C)")
            else:
                print(f"  UTCI  (skipped — weather API unavailable)")
        else:
            print(f"  Wind  {stats['wind']['mean_ms']} m/s mean | "
                  f"{stats['wind']['frac_lt1ms']*100:.0f}% stagnant (<1 m/s)")
            print(f"  Sun   {stats['sun']['mean_hrs_day']} h/day (Jul) | "
                  f"{stats['sun']['frac_gt5h']*100:.0f}% > 5 h/day (overexposed)")
            if stats["utci"]:
                print(f"  UTCI  {stats['utci']['mean_c']} deg C (Jul) | "
                      f"{stats['utci']['frac_utci_bad']*100:.0f}% heat stress (>{thr} C)")
            else:
                print(f"  UTCI  (skipped — weather API unavailable)")

        print(f"\n  -> results/{site_key}/  baseline_wind/sun/utci .png + stats.json")
        return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()), required=True)
    parser.add_argument("--size", type=int, choices=[500, 1000], default=500)
    parser.add_argument("--cached", action="store_true",
                        help="Skip API fetch — load buildings/veg/ground from fetched_data.json")
    parser.add_argument("--buffer", type=int, default=None,
                        help="Context buffer in metres each side (default: 500 for 500m, 500 for 1km)")
    args = parser.parse_args()
    main(args.site, size=args.size, cached=args.cached, buffer_m=args.buffer)
