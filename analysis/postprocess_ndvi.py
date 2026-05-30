"""
postprocess_ndvi.py — Convert GEE NDVI canopy polygons → simulation tree features
===================================================================================
Takes the GeoJSON polygon export from gee_ndvi_canopy.js, clips canopy patches
by building footprints (no tree inside a building), then converts each surviving
patch to one or more GeoJSON Point features compatible with the Infrared SDK's
vegetation argument.

Input:
    --site     : almaty | riyadh | astana | mecca
    --geojson  : path to <City>_canopy_polygons.geojson  (from GEE Drive export)

Output:
    analysis/results/<site>/ndvi_trees.json
    — list of GeoJSON Point features, each with:
        properties.height       (m)
        properties.crown_radius (m)
        properties.genus        (Betula | Phoenix | Ulmus …)
        properties.source       "ndvi"

Requires:
    pip install shapely

Usage:
    python postprocess_ndvi.py --site almaty --geojson ~/Downloads/Almaty_canopy_polygons.geojson
    python postprocess_ndvi.py --site astana --geojson ~/Downloads/Astana_canopy_polygons.geojson
    python postprocess_ndvi.py --site riyadh --geojson ~/Downloads/Riyadh_canopy_polygons.geojson
    python postprocess_ndvi.py --site mecca  --geojson ~/Downloads/Mecca_canopy_polygons.geojson

After running, re-execute baseline.py for the same site — it will automatically
pick up ndvi_trees.json and use it instead of the sparse OSM vegetation data.
"""

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from shapely.geometry import shape, Polygon, MultiPolygon, Point
    from shapely.strtree import STRtree
    HAS_SHAPELY = True
except ImportError:
    print("ERROR: shapely not installed.  Run: pip install shapely")
    HAS_SHAPELY = False

# Allow importing sites.py from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from sites import SITES


# ── Tunables ─────────────────────────────────────────────────────────────────
MIN_PATCH_M2     = 15    # m² — patches smaller than this are noise, skip them
GRID_SPACING_M   = 10    # m — grid spacing when placing trees inside large patches
MAX_CROWN_M      = 6.0   # m — cap on auto-estimated crown radius


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _analysis_sw(lat_c: float, lon_c: float):
    """Return (lat, lon) of the SW corner of the 500 m analysis polygon."""
    half_lat = 250 / 111_320
    half_lon = 250 / (111_320 * math.cos(math.radians(lat_c)))
    return lat_c - half_lat, lon_c - half_lon


def _to_local(lat: float, lon: float, orig_lat: float, orig_lon: float):
    """WGS84 → local metres from the analysis-polygon SW corner."""
    x = (lon - orig_lon) * 111_320 * math.cos(math.radians(orig_lat))
    y = (lat - orig_lat) * 111_320
    return x, y


def _poly_area_m2(poly: Polygon, orig_lat: float) -> float:
    """
    Approximate polygon area in m².
    poly.area is in degrees²; scale by (m/deg)² at the given latitude.
    Accurate to ~1 % for patches up to a few hundred metres.
    """
    lat_scale = 111_320
    lon_scale = 111_320 * math.cos(math.radians(orig_lat))
    return abs(poly.area) * lat_scale * lon_scale


# ── Building footprints ───────────────────────────────────────────────────────

def _load_building_shapes(fetched_json: Path, orig_lat: float, orig_lon: float):
    """
    Return a list of Shapely Polygons in LOCAL metres reconstructed from the
    bounding boxes of every DotBimMesh in fetched_data.json.
    Used to exclude tree placement inside buildings.
    """
    with open(fetched_json) as f:
        data = json.load(f)

    polys = []
    for mesh_dict in data.get("buildings", {}).values():
        coords = mesh_dict.get("coordinates", [])
        xs = coords[0::3]
        ys = coords[1::3]
        if len(xs) < 3:
            continue
        polys.append(Polygon(list(zip(xs, ys))))
    return polys


# ── Canopy patch → tree points ────────────────────────────────────────────────

def _make_tree(lat: float, lon: float,
               orig_lat: float, orig_lon: float,
               height: float, crown_radius: float, genus: str,
               bldg_tree: "STRtree", bldg_polys):
    """
    Return a GeoJSON Point feature for one tree, or None if the point
    falls inside a building footprint.
    """
    x, y = _to_local(lat, lon, orig_lat, orig_lon)
    pt   = Point(x, y)
    for idx in bldg_tree.query(pt):
        if bldg_polys[idx].contains(pt):
            return None   # inside a building — skip

    return {
        "type": "Feature",
        "geometry": {
            "type":        "Point",
            "coordinates": [round(lon, 7), round(lat, 7)],
        },
        "properties": {
            "height":       height,
            "crown_radius": round(crown_radius, 2),
            "genus":        genus,
            "source":       "ndvi",
        },
    }


def _patch_to_trees(poly_deg: Polygon,
                    orig_lat: float, orig_lon: float,
                    height: float, crown_radius: float, genus: str,
                    bldg_tree: "STRtree", bldg_polys):
    """
    Convert one canopy polygon (WGS84 degrees) to a list of tree Point features.

    Small patches  (< 4 × crown-area)  → single tree at centroid.
    Larger patches → regular grid at GRID_SPACING_M to represent multiple trees.
    """
    area_m2 = _poly_area_m2(poly_deg, orig_lat)
    if area_m2 < MIN_PATCH_M2:
        return []

    out = []

    single_threshold = math.pi * (crown_radius * 2) ** 2   # area of 2-crown-dia circle

    if area_m2 < single_threshold:
        # ── Small patch: one tree at centroid ────────────────────────────
        c = poly_deg.centroid
        r = min(math.sqrt(area_m2 / math.pi), MAX_CROWN_M)
        t = _make_tree(c.y, c.x, orig_lat, orig_lon,
                       height, r, genus, bldg_tree, bldg_polys)
        if t:
            out.append(t)
    else:
        # ── Large patch: grid of trees ────────────────────────────────────
        # Place tree centres every GRID_SPACING_M metres, offset by half-step
        # from the patch bounding box so edge trees aren't on the boundary.
        spacing_lat = GRID_SPACING_M / 111_320
        spacing_lon = GRID_SPACING_M / (111_320 * math.cos(math.radians(orig_lat)))
        minx, miny, maxx, maxy = poly_deg.bounds

        lat = miny + spacing_lat / 2
        while lat <= maxy:
            lon = minx + spacing_lon / 2
            while lon <= maxx:
                if poly_deg.contains(Point(lon, lat)):
                    t = _make_tree(lat, lon, orig_lat, orig_lon,
                                   height, crown_radius, genus,
                                   bldg_tree, bldg_polys)
                    if t:
                        out.append(t)
                lon += spacing_lon
            lat += spacing_lat

    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main(site_key: str, geojson_path: Path):
    if not HAS_SHAPELY:
        sys.exit(1)

    site               = SITES[site_key]
    lat_c, lon_c       = site["lat"], site["lon"]
    orig_lat, orig_lon = _analysis_sw(lat_c, lon_c)
    climate            = site["climate"]

    out_dir      = Path(__file__).parent / "results" / site_key
    fetched_json = out_dir / "fetched_data.json"

    if not fetched_json.exists():
        print(f"ERROR: {fetched_json} not found.")
        print(f"       Run baseline.py --site {site_key} first to populate the cache.")
        sys.exit(1)

    # ── Load building footprints (for tree-placement clipping) ─────────────
    print(f"[1/3] Loading buildings from {fetched_json.name} ...")
    bldg_polys = _load_building_shapes(fetched_json, orig_lat, orig_lon)
    bldg_tree  = STRtree(bldg_polys)
    print(f"      {len(bldg_polys)} building footprints")

    # ── Load canopy polygons from GEE export ──────────────────────────────
    print(f"[2/3] Loading canopy polygons from {geojson_path.name} ...")
    with open(geojson_path) as f:
        gj = json.load(f)
    features = gj.get("features", [])
    print(f"      {len(features)} canopy polygon features")

    # Default genus / dimensions from climate type if not annotated by GEE
    default_genus  = "Phoenix" if climate == "hot" else "Betula"
    default_height = 10 if climate == "hot" else 8
    default_crown  = 4  if climate == "hot" else 3

    # ── Convert polygons → tree points ────────────────────────────────────
    print("[3/3] Converting canopy patches to tree points ...")
    all_trees = []
    for feat in features:
        geom  = shape(feat["geometry"])
        props = feat.get("properties") or {}

        genus        = props.get("genus")        or default_genus
        tree_height  = float(props.get("tree_height")  or default_height)
        crown_radius = float(props.get("crown_radius") or default_crown)

        sub_polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        for poly in sub_polys:
            if not isinstance(poly, Polygon) or poly.is_empty:
                continue
            trees = _patch_to_trees(
                poly, orig_lat, orig_lon,
                tree_height, crown_radius, genus,
                bldg_tree, bldg_polys,
            )
            all_trees.extend(trees)

    print(f"      {len(all_trees)} tree points generated")
    if not all_trees:
        print("WARNING: 0 tree points — check GEE export coordinates "
              "and NDVI threshold.")
        print("         The GEE bounding boxes must match the site centres in sites.py.")
        return

    # ── Save ──────────────────────────────────────────────────────────────
    out_path = out_dir / "ndvi_trees.json"
    with open(out_path, "w") as f:
        json.dump(all_trees, f, separators=(",", ":"))

    inside_500m = 0
    for t in all_trees:
        lon_t, lat_t = t["geometry"]["coordinates"]
        x, y = _to_local(lat_t, lon_t, orig_lat, orig_lon)
        if 0 <= x <= 500 and 0 <= y <= 500:
            inside_500m += 1

    print()
    print(f"Saved  {out_path}")
    print(f"  Total trees  : {len(all_trees)}")
    print(f"  In 500 m zone: {inside_500m}  "
          f"(rest are in the 1500 m context — used for CFD boundary conditions)")
    print()
    print("Next step — re-run baseline.py to include NDVI trees in the simulation:")
    print(f"  python baseline.py --site {site_key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert GEE NDVI canopy polygons to Infrared SDK tree features"
    )
    parser.add_argument("--site",    required=True, choices=list(SITES.keys()),
                        help="Site key (almaty | riyadh | astana | mecca)")
    parser.add_argument("--geojson", required=True,
                        help="Path to <City>_canopy_polygons.geojson from GEE Drive export")
    args = parser.parse_args()
    main(args.site, Path(args.geojson))
