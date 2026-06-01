"""
fetch_ms_buildings.py — Microsoft Global ML Building Footprints enrichment
==========================================================================
Downloads ML-derived building footprints from Microsoft's open dataset,
deduplicates against the existing OSM + Overture set, and merges new
buildings into fetched_data.json for each site/size.

The data is line-delimited GeoJSON (.csv.gz) partitioned by Bing quadkey.
Coverage: 1.4B buildings worldwide including Saudi Arabia & Kazakhstan.

Usage:
    python fetch_ms_buildings.py
    python fetch_ms_buildings.py --site mecca --size 1000
"""

import argparse
import gzip
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

from sites import SITES

ANALYSIS_DIR = Path(__file__).parent
IOU_THRESHOLD = 0.20       # slightly lower than Overture — MS footprints are ML-derived
DEFAULT_HEIGHT = 9.0       # fallback when height = -1
MS_ID_START = 190_000      # base mesh_id (above Overture's 90k range)

# ---------------------------------------------------------------------------
# Quadkey logic (Bing Maps tile system)
# ---------------------------------------------------------------------------

def _latlon_to_quadkey(lat: float, lon: float, level: int = 9) -> str:
    sin_lat = math.sin(lat * math.pi / 180)
    sin_lat = max(-0.9999, min(0.9999, sin_lat))
    pixel_x = ((lon + 180) / 360) * (256 << level)
    pixel_y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * (256 << level)
    tile_x = int(pixel_x / 256)
    tile_y = int(pixel_y / 256)
    quadkey = ""
    for i in range(level, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if (tile_x & mask) != 0:
            digit += 1
        if (tile_y & mask) != 0:
            digit += 2
        quadkey += str(digit)
    return quadkey


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def _analysis_sw(lat_c: float, lon_c: float, size: int = 500) -> Tuple[float, float]:
    half_lat = (size / 2) / 111_320
    half_lon = (size / 2) / (111_320 * math.cos(math.radians(lat_c)))
    return lat_c - half_lat, lon_c - half_lon


def _to_local(lat: float, lon: float,
              orig_lat: float, orig_lon: float) -> Tuple[float, float]:
    x = (lon - orig_lon) * 111_320 * math.cos(math.radians(orig_lat))
    y = (lat - orig_lat) * 111_320
    return x, y


def _context_bbox(lat_c: float, lon_c: float, size: int = 500) -> Tuple[float, float, float, float]:
    """(west, south, east, north) for the context polygon."""
    ctx = 1500 if size == 500 else 2000
    half_lat = (ctx / 2) / 111_320
    half_lon = (ctx / 2) / (111_320 * math.cos(math.radians(lat_c)))
    return (lon_c - half_lon, lat_c - half_lat,
            lon_c + half_lon, lat_c + half_lat)


# ---------------------------------------------------------------------------
# Spatial deduplication (bbox-based, fast)
# ---------------------------------------------------------------------------

def _bbox_from_coords(coords: list) -> Tuple[float, float, float, float]:
    """(xmin, ymin, xmax, ymax) from a flat [x,y,z,...] list."""
    xs = coords[0::3]
    ys = coords[1::3]
    return min(xs), min(ys), max(xs), max(ys)


def _iou_bbox(a: Tuple, b: Tuple) -> float:
    """IoU of two axis-aligned bounding boxes."""
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    if area_a + area_b - inter <= 0:
        return 0.0
    return inter / (area_a + area_b - inter)


def _is_duplicate(ms_bbox: Tuple, existing_bboxes: List[Tuple]) -> bool:
    for eb in existing_bboxes:
        if _iou_bbox(ms_bbox, eb) >= IOU_THRESHOLD:
            return True
    return False


# ---------------------------------------------------------------------------
# DotBimMesh construction (matches fetch_overture.py format)
# ---------------------------------------------------------------------------

def _poly_to_mesh(ring_lonlat: List, height: float, mesh_id: int,
                  orig_lat: float, orig_lon: float) -> dict:
    """Extrude polygon ring to a 3D mesh dict (same format as fetched_data.json)."""
    pts = [_to_local(lat, lon, orig_lat, orig_lon)
           for (lon, lat) in ring_lonlat[:-1]]  # drop closing vertex
    n = len(pts)
    if n < 3:
        return None

    h = max(height, 1.0)
    coords = []
    for (x, y) in pts:
        coords += [x, y, 0.0]
    for (x, y) in pts:
        coords += [x, y, h]

    indices = []
    for i in range(1, n - 1):
        indices += [0, i + 1, i]
    for i in range(1, n - 1):
        indices += [n, n + i, n + i + 1]
    for i in range(n):
        j = (i + 1) % n
        indices += [i, j, n + j, i, n + j, n + i]

    return {
        "mesh_id": mesh_id,
        "coordinates": coords,
        "indices": indices,
    }


# ---------------------------------------------------------------------------
# Download + merge
# ---------------------------------------------------------------------------

def _find_tile_url(quadkey: str) -> str:
    """Look up the download URL for a quadkey from dataset-links.csv."""
    import requests
    links_url = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"

    cache_path = ANALYSIS_DIR / "cache" / "ms_dataset_links.csv"
    if cache_path.exists():
        text = cache_path.read_text()
    else:
        print("  [ms-bldg] downloading dataset-links.csv index...")
        r = requests.get(links_url, timeout=60)
        r.raise_for_status()
        text = r.text
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text)

    for line in text.strip().split("\n")[1:]:
        parts = line.split(",")
        if len(parts) >= 3 and parts[1] == quadkey:
            return parts[2]
    return None


def fetch_ms_buildings(site_key: str, size: int = 500) -> int:
    """Download MS buildings for a site, merge into fetched_data.json. Returns count added."""
    import requests

    site = SITES[site_key]
    lat_c, lon_c = site["lat"], site["lon"]
    subdir = "1km" if size == 1000 else ""
    src = ANALYSIS_DIR / "results" / site_key / (subdir or ".")

    fetched_path = src / "fetched_data.json"
    if not fetched_path.exists():
        print(f"  [{site_key}/{subdir or '500m'}] no fetched_data.json — skipped")
        return 0

    # Load existing buildings
    with open(fetched_path) as f:
        data = json.load(f)

    buildings = data.get("buildings", {})
    # Use 500m analysis polygon origin (same convention as fetch_overture.py)
    orig_lat, orig_lon = _analysis_sw(lat_c, lon_c, 500)

    # Check if already enriched
    ms_count = sum(1 for k in buildings if k.startswith("ms_"))
    if ms_count > 0:
        print(f"  [{site_key}/{subdir or '500m'}] already has {ms_count} MS buildings — skipped")
        return 0

    # Build existing bboxes in WGS84 for dedup (mixed origins in local space)
    ctx_size = 1500 if size == 500 else 2000
    osm_orig = _analysis_sw(lat_c, lon_c, ctx_size)
    ov_orig  = _analysis_sw(lat_c, lon_c, 500)
    existing_bboxes_wgs = []
    for bid, mesh in buildings.items():
        coords = mesh.get("coordinates", [])
        if len(coords) < 9:
            continue
        o = ov_orig if bid.startswith("ov_") else osm_orig
        xs = coords[0::3]
        ys = coords[1::3]
        # Convert local bbox to WGS84 bbox (lon_min, lat_min, lon_max, lat_max)
        lon_min = o[1] + min(xs) / (111_320 * math.cos(math.radians(o[0])))
        lon_max = o[1] + max(xs) / (111_320 * math.cos(math.radians(o[0])))
        lat_min = o[0] + min(ys) / 111_320
        lat_max = o[0] + max(ys) / 111_320
        existing_bboxes_wgs.append((lon_min, lat_min, lon_max, lat_max))

    # Find the quadkey and download URL
    quadkey = _latlon_to_quadkey(lat_c, lon_c, level=9)
    tile_url = _find_tile_url(quadkey)
    if not tile_url:
        print(f"  [{site_key}] no MS tile for quadkey {quadkey}")
        return 0

    # Download tile (may be large — cache it)
    cache_file = ANALYSIS_DIR / "cache" / f"ms_{quadkey}.geojsonl.gz"
    if cache_file.exists():
        print(f"  [{site_key}] using cached MS tile {quadkey}")
        raw = cache_file.read_bytes()
    else:
        print(f"  [{site_key}] downloading MS tile {quadkey} ...")
        r = requests.get(tile_url, timeout=180)
        r.raise_for_status()
        raw = r.content
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(raw)
        print(f"  [{site_key}] downloaded {len(raw)/1024/1024:.1f} MB")

    text = gzip.decompress(raw).decode("utf-8")
    lines = text.strip().split("\n")
    print(f"  [{site_key}] tile has {len(lines)} buildings total")

    # Filter to context bbox
    bbox = _context_bbox(lat_c, lon_c, size)
    added = 0

    for line in lines:
        feat = json.loads(line)
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue

        ring = geom["coordinates"][0]
        lons = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        clat = sum(lats) / len(lats)
        clon = sum(lons) / len(lons)

        # Skip if outside context bbox
        if not (bbox[0] <= clon <= bbox[2] and bbox[1] <= clat <= bbox[3]):
            continue

        # Height
        props = feat.get("properties", {})
        height = props.get("height", -1)
        if height is None or height < 0:
            height = DEFAULT_HEIGHT

        # Dedup in WGS84 space (existing buildings have mixed local origins)
        ms_bbox_wgs = (min(lons), min(lats), max(lons), max(lats))
        if _is_duplicate(ms_bbox_wgs, existing_bboxes_wgs):
            continue

        # Build mesh
        mesh = _poly_to_mesh(ring, height, MS_ID_START + added, orig_lat, orig_lon)
        if mesh is None:
            continue

        bid = f"ms_{added:05d}"
        buildings[bid] = mesh
        existing_bboxes_wgs.append(ms_bbox_wgs)  # add to dedup set
        added += 1

    if added > 0:
        data["buildings"] = buildings
        with open(fetched_path, "w") as f:
            json.dump(data, f)
        tag = f"{site_key}/1km" if size == 1000 else site_key
        n_osm = sum(1 for k in buildings if not k.startswith(("ov_", "ms_")))
        n_ov = sum(1 for k in buildings if k.startswith("ov_"))
        n_ms = sum(1 for k in buildings if k.startswith("ms_"))
        print(f"  [{tag}] +{added} MS buildings (total: {n_osm} OSM + {n_ov} Overture + {n_ms} MS = {len(buildings)})")
    else:
        tag = f"{site_key}/1km" if size == 1000 else site_key
        print(f"  [{tag}] 0 new MS buildings (all duplicates)")

    return added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()), default=None)
    parser.add_argument("--size", type=int, choices=[500, 1000], default=None)
    args = parser.parse_args()

    print("\n=== Fetching Microsoft Building Footprints ===")

    if args.site:
        sizes = [args.size] if args.size else [500, 1000]
        for s in sizes:
            fetch_ms_buildings(args.site, s)
    else:
        for site_key in SITES:
            for s in [500, 1000]:
                fetch_ms_buildings(site_key, s)

    print("\nDone. Now re-run export_buildings_geojson.py to regenerate GeoJSON overlays.")


if __name__ == "__main__":
    main()
