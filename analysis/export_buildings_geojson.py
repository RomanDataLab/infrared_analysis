"""
Export building footprints from fetched_data.json as GeoJSON for frontend overlay.
Three sources (OSM, Overture, MS) are merged with priority-based spatial dedup.

Usage:
    python export_buildings_geojson.py
    python export_buildings_geojson.py --site mecca --size 1000

Outputs -> public/heatmaps/<site>[/1km]/buildings.geojson
"""

import argparse
import json
import math
from pathlib import Path
from collections import defaultdict
from sites import SITES

ANALYSIS_DIR = Path(__file__).parent
PUBLIC_DIR   = ANALYSIS_DIR.parent / "public"

# Merge priority: lower = higher priority (kept over others)
SOURCE_PRIORITY = {"osm": 0, "overture": 1, "ms": 2}
# IoU threshold for duplicate detection
IOU_THRESHOLD = 0.10


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def _analysis_sw(lat_c, lon_c, size=500):
    """SW corner of the analysis polygon — origin of the local coord system."""
    half_lat = (size / 2) / 111_320
    half_lon = (size / 2) / (111_320 * math.cos(math.radians(lat_c)))
    return lat_c - half_lat, lon_c - half_lon


def _to_wgs84(x, y, orig_lat, orig_lon):
    """Local metres -> WGS84 (lon, lat)."""
    lat = orig_lat + y / 111_320
    lon = orig_lon + x / (111_320 * math.cos(math.radians(orig_lat)))
    return lon, lat


# ---------------------------------------------------------------------------
# Convex hull footprint extraction
# ---------------------------------------------------------------------------

def mesh_to_footprint(mesh_data, orig_lat, orig_lon):
    """
    Extract the ground-level 2D footprint from a DotBimMesh as a convex hull.
    Returns a GeoJSON Polygon ring (list of [lon, lat]) or None.
    """
    coords = mesh_data.get("coordinates", [])
    if len(coords) < 9:
        return None

    xs = coords[0::3]
    ys = coords[1::3]
    zs = coords[2::3]
    z_min = min(zs)
    z_thresh = z_min + 0.5

    seen = set()
    points = []
    for i, z in enumerate(zs):
        if z <= z_thresh:
            key = (round(xs[i], 2), round(ys[i], 2))
            if key not in seen:
                seen.add(key)
                points.append((xs[i], ys[i]))

    if len(points) < 3:
        return None

    hull = _convex_hull(points)
    if hull is None:
        return None

    ring = [list(_to_wgs84(x, y, orig_lat, orig_lon)) for x, y in hull]
    ring.append(ring[0])
    return ring


def _convex_hull(points):
    """Andrew's monotone chain convex hull. Returns ordered list of (x,y) or None."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return None

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return hull if len(hull) >= 3 else None


# ---------------------------------------------------------------------------
# Spatial dedup: priority-based merge
# ---------------------------------------------------------------------------

def _bbox(ring):
    """Bounding box (lon_min, lat_min, lon_max, lat_max) from a GeoJSON ring."""
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (min(lons), min(lats), max(lons), max(lats))


def _bbox_area(b):
    return (b[2] - b[0]) * (b[3] - b[1])


def _bbox_iou(a, b):
    """IoU of two axis-aligned bounding boxes."""
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = _bbox_area(a) + _bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def _bbox_contains(outer, inner):
    """True if inner bbox is fully inside outer bbox."""
    return (inner[0] >= outer[0] and inner[1] >= outer[1] and
            inner[2] <= outer[2] and inner[3] <= outer[3])


class SpatialGrid:
    """Simple grid-based spatial index for fast neighbour lookup."""

    def __init__(self, cell_deg=0.001):
        self.cell = cell_deg  # ~111 m at equator
        self.grid = defaultdict(list)

    def _key(self, lon, lat):
        return (int(lon / self.cell), int(lat / self.cell))

    def insert(self, idx, bbox):
        # Insert into all grid cells the bbox touches
        x0, y0 = self._key(bbox[0], bbox[1])
        x1, y1 = self._key(bbox[2], bbox[3])
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                self.grid[(gx, gy)].append(idx)

    def query(self, bbox):
        """Return indices of items whose grid cells overlap this bbox."""
        x0, y0 = self._key(bbox[0], bbox[1])
        x1, y1 = self._key(bbox[2], bbox[3])
        hits = set()
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                for idx in self.grid.get((gx, gy), []):
                    hits.add(idx)
        return hits


def _is_duplicate(ring, bbox, grid, accepted_rings, accepted_bboxes):
    """Check if a building overlaps any already-accepted building."""
    for idx in grid.query(bbox):
        if _bbox_iou(bbox, accepted_bboxes[idx]) >= IOU_THRESHOLD:
            return True
    return False


def merge_buildings(features):
    """
    Priority-based spatial merge: OSM > Overture > MS.
    Returns deduplicated feature list.
    """
    # Sort by priority (OSM first, then Overture, then MS)
    features.sort(key=lambda f: SOURCE_PRIORITY.get(f["properties"]["source"], 9))

    grid = SpatialGrid(cell_deg=0.0005)  # ~55 m cells
    accepted = []
    accepted_rings = []
    accepted_bboxes = []
    dupes = {"osm": 0, "overture": 0, "ms": 0}

    for feat in features:
        ring = feat["geometry"]["coordinates"][0]
        bb = _bbox(ring)
        if _is_duplicate(ring, bb, grid, accepted_rings, accepted_bboxes):
            dupes[feat["properties"]["source"]] += 1
            continue
        idx = len(accepted)
        grid.insert(idx, bb)
        accepted_rings.append(ring)
        accepted_bboxes.append(bb)
        accepted.append(feat)

    total_dupes = sum(dupes.values())
    if total_dupes > 0:
        parts = [f"{v} {k}" for k, v in dupes.items() if v > 0]
        print(f"    dedup removed {total_dupes} ({', '.join(parts)})")

    # Pass 2: remove smaller buildings fully contained inside larger ones
    accepted = _remove_contained(accepted, accepted_bboxes)

    return accepted


def _remove_contained(features, bboxes):
    """Remove buildings whose bbox is fully inside a larger building's bbox."""
    n = len(features)
    if n < 2:
        return features

    # Build index of (area, original_index), sorted largest first
    indexed = sorted(range(n), key=lambda i: _bbox_area(bboxes[i]), reverse=True)

    grid = SpatialGrid(cell_deg=0.0005)
    # Insert all buildings into grid keyed by their original index
    for i in range(n):
        grid.insert(i, bboxes[i])

    removed = set()
    for i in indexed:
        if i in removed:
            continue
        bb_outer = bboxes[i]
        # Find candidates that overlap this building's grid cells
        for j in grid.query(bb_outer):
            if j == i or j in removed:
                continue
            # If j is smaller and fully contained in i, mark for removal
            if _bbox_area(bboxes[j]) < _bbox_area(bb_outer) and _bbox_contains(bb_outer, bboxes[j]):
                removed.add(j)

    if removed:
        by_src = {}
        for j in removed:
            s = features[j]["properties"]["source"]
            by_src[s] = by_src.get(s, 0) + 1
        parts = [f"{v} {k}" for k, v in by_src.items() if v > 0]
        print(f"    containment removed {len(removed)} ({', '.join(parts)})")

    return [f for i, f in enumerate(features) if i not in removed]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_site(site_key, size=500):
    site = SITES[site_key]
    subdir = "1km" if size == 1000 else ""
    src = ANALYSIS_DIR / "results" / site_key / (subdir or ".")
    dst = PUBLIC_DIR / "heatmaps" / site_key / (subdir or ".")

    fetched_path = src / "fetched_data.json"
    if not fetched_path.exists():
        print(f"  [{site_key}/{subdir or '500m'}] no fetched_data.json — skipped")
        return 0

    with open(fetched_path) as f:
        data = json.load(f)

    buildings = data.get("buildings", {})
    ctx_size = 1500 if size == 500 else 2000
    orig_osm_lat, orig_osm_lon = _analysis_sw(site["lat"], site["lon"], ctx_size)
    orig_ov_lat,  orig_ov_lon  = _analysis_sw(site["lat"], site["lon"], 500)

    # Step 1: extract all footprints
    raw_features = []
    for bid, mesh in buildings.items():
        is_enriched = bid.startswith(("ov_", "ms_"))
        if is_enriched:
            o_lat, o_lon = orig_ov_lat, orig_ov_lon
        else:
            o_lat, o_lon = orig_osm_lat, orig_osm_lon

        ring = mesh_to_footprint(mesh, o_lat, o_lon)
        if ring is None:
            continue

        source = "ms" if bid.startswith("ms_") else ("overture" if bid.startswith("ov_") else "osm")
        height = None
        coords = mesh.get("coordinates", [])
        if coords:
            zs = coords[2::3]
            height = round(max(zs), 1) if zs else None

        raw_features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "id": bid,
                "source": source,
                "height": height,
            },
        })

    # Save per-source GeoJSON (unmerged, for rollback)
    dst.mkdir(parents=True, exist_ok=True)
    for src_name in ("osm", "overture", "ms"):
        src_feats = [f for f in raw_features if f["properties"]["source"] == src_name]
        if not src_feats:
            continue
        src_gj = {"type": "FeatureCollection", "features": src_feats}
        with open(dst / f"buildings_{src_name}.geojson", "w") as f:
            json.dump(src_gj, f)

    # Step 2: priority-based spatial merge
    features = merge_buildings(raw_features)

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = dst / "buildings.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)

    # Save merged IDs so baseline.py can filter DotBimMesh buildings to match
    merged_ids = [f["properties"]["id"] for f in features]
    ids_path = src / "merged_ids.json"
    with open(ids_path, "w") as f:
        json.dump(merged_ids, f)

    n_osm = sum(1 for f in features if f["properties"]["source"] == "osm")
    n_ov  = sum(1 for f in features if f["properties"]["source"] == "overture")
    n_ms  = sum(1 for f in features if f["properties"]["source"] == "ms")
    tag = f"{site_key}/1km" if size == 1000 else site_key
    parts = [f"{n_osm} OSM"]
    if n_ov:
        parts.append(f"{n_ov} Overture")
    if n_ms:
        parts.append(f"{n_ms} MS")
    before = len(raw_features)
    print(f"  [{tag}] {before} raw -> {len(features)} merged ({' + '.join(parts)})")
    print(f"    saved {len(merged_ids)} merged IDs -> {ids_path.name}")
    return len(features)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()), default=None)
    parser.add_argument("--size", type=int, choices=[500, 1000], default=None)
    args = parser.parse_args()

    print("\n=== Exporting building footprint GeoJSON (with spatial merge) ===")

    if args.site:
        sizes = [args.size] if args.size else [500, 1000]
        for s in sizes:
            export_site(args.site, s)
    else:
        for site_key in SITES:
            for s in [500, 1000]:
                export_site(site_key, s)


if __name__ == "__main__":
    main()
