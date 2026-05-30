"""
Regenerate map-overlay PNGs from existing .npy grids.

These are pure RGBA images (no colorbar, no title, NaN = transparent) meant
to be placed as Leaflet imageOverlay — the whole image covers the analysis
polygon exactly, so geographic alignment is pixel-perfect.

Run once after fixing baseline/scenarios; thereafter save_heatmap() in each
analysis script auto-saves the overlay alongside the thumbnail.

Usage:
    python regen_overlays.py
"""

import sys
import numpy as np
from pathlib import Path
from matplotlib import cm
from matplotlib.colors import Normalize
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).parent))
from sites import SITES

RESULTS = Path(__file__).parent / "results"
PUBLIC  = Path(__file__).parent.parent / "public" / "heatmaps"

DAYS_IN_MONTH = {1:31,2:28,3:31,4:30,5:31,6:30,
                 7:31,8:31,9:30,10:31,11:30,12:31}


def _fill_nan_smooth_fade(grid, sigma=20, fade_px=100):
    """Fill NaN cells, smooth the filled region, and return a distance-based alpha.

    Returns (render_grid, alpha_2d):
      - render_grid : full grid with NaN filled via nearest-neighbour + Gaussian blur
                      (sigma px).  Original valid pixels are restored exactly.
      - alpha_2d    : float32 array [0..1].  Valid pixels = 1.0.  NaN-filled pixels
                      fade linearly from 1.0 (at the valid-data boundary) to 0.0 at
                      fade_px pixels away, then stay 0.  This makes the corners of
                      the bounding box dissolve naturally rather than showing an
                      obviously interpolated block.

    sigma=20 px erases spoke artefacts; fade_px=100 ≈ 100 m on a 512-px/500-m grid.
    """
    nan_mask = np.isnan(grid)
    if not nan_mask.any():
        return grid, np.ones(grid.shape, dtype=np.float32)

    # Step 1: distance from every NaN cell to the nearest valid cell
    dist, (row_idx, col_idx) = distance_transform_edt(
        nan_mask, return_distances=True, return_indices=True
    )

    # Step 2: nearest-neighbour fill
    filled = grid.copy()
    filled[nan_mask] = grid[row_idx[nan_mask], col_idx[nan_mask]]

    # Step 3: heavy Gaussian blur on the filled grid
    blurred = gaussian_filter(filled, sigma=sigma)

    # Step 4: restore original valid pixels (blur only the filled region)
    result = blurred.copy()
    result[~nan_mask] = grid[~nan_mask]

    # Step 5: alpha channel — valid=1.0, filled fades 1→0 over fade_px pixels
    alpha = np.ones(grid.shape, dtype=np.float32)
    alpha[nan_mask] = np.clip(1.0 - dist[nan_mask] / fade_px, 0.0, 1.0)

    return result, alpha


def save_overlay(grid, out_path, cmap_name, vmin=None, vmax=None,
                 fill_nan=False):
    """Save a clean RGBA PNG suitable for Leaflet imageOverlay.

    Row 0 of the Infrared grid = south edge.  We flip vertically so the
    top of the PNG = north, which is where Leaflet places it when the
    bounds are [[lat_sw, lon_sw], [lat_ne, lon_ne]].

    fill_nan : if True, NaN cells are filled with smooth interpolation and
               a distance-based alpha fade so the real-data boundary dissolves
               naturally into the base map.  If False, NaN = transparent.
    """
    cmap_obj = cm.get_cmap(cmap_name).copy()
    cmap_obj.set_bad(alpha=0)

    if vmin is None:
        vmin = float(np.nanpercentile(grid, 2))
    if vmax is None:
        vmax = float(np.nanpercentile(grid, 98))

    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)

    if fill_nan:
        render_grid, fill_alpha = _fill_nan_smooth_fade(grid)
        rgba = cmap_obj(norm(np.flipud(render_grid)))          # (H,W,4) float
        rgba[..., 3] = np.flipud(fill_alpha)                   # overwrite alpha
    else:
        rgba = cmap_obj(norm(np.flipud(grid)))                 # NaN → alpha=0

    rgba_u8 = (np.clip(rgba, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(rgba_u8, "RGBA").save(out_path)

    nan_pct = np.isnan(grid).mean() * 100
    fill_tag = f"  [NaN-filled {nan_pct:.0f}%]" if fill_nan and nan_pct > 0 else ""
    print(f"    {out_path.name}  {grid.shape[1]}×{grid.shape[0]}px  "
          f"vmin={vmin:.2f} vmax={vmax:.2f}{fill_tag}")


def process_site(site_key):
    site = SITES[site_key]
    src  = RESULTS / site_key
    dst  = PUBLIC  / site_key
    dst.mkdir(parents=True, exist_ok=True)

    climate     = site["climate"]
    solar_cmap  = site["solar_cmap"]
    utci_cmap   = "RdYlBu_r" if climate == "hot" else "RdYlBu"
    solar_month = site["solar_month"]
    days        = DAYS_IN_MONTH[solar_month]

    layers = [
        # (npy stem,        out stem,             cmap,       transform,        fill_nan)
        # Wind: fill NaN edges — the API's circular CFD domain doesn't always
        # cover the full rectangular bounding box (especially for directional wind
        # with upwind padding).  Nearest-neighbour fill gives a seamless overlay.
        ("baseline_wind",  "baseline_wind",   "YlOrRd",    None,              True),
        ("baseline_sun",   "baseline_sun",    solar_cmap,  lambda g: g / days, False),
        ("baseline_utci",  "baseline_utci",   utci_cmap,   None,              False),
    ]

    print(f"\n  [{site_key}]")
    for npy_stem, out_stem, cmap_name, transform, fill_nan in layers:
        npy_path = src / f"{npy_stem}.npy"
        if not npy_path.exists():
            print(f"    skip (missing): {npy_stem}.npy")
            continue
        grid = np.load(npy_path)
        if transform:
            grid = transform(grid)
        out_name = f"{out_stem}_overlay.png"
        save_overlay(grid, dst / out_name, cmap_name, fill_nan=fill_nan)
        # Also update the results/ copy so export_web.py picks up the fixed PNG
        results_out = src / out_name
        if results_out.exists() or fill_nan:
            import shutil
            shutil.copy2(dst / out_name, results_out)


if __name__ == "__main__":
    print("=== Regenerating map-overlay PNGs ===")
    for key in SITES:
        process_site(key)
    print("\nDone — overlay PNGs written to public/heatmaps/")
