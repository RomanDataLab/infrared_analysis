"""
Export tree canopy geometry as GeoJSON for frontend overlay.
Two sources:
  1. OSM tree points -> circular canopy polygons (from fetched_data.json)
  2. Ground-material vegetation zones (parks/woods/grass from fetched_data.json)

Usage:
    python export_trees_geojson.py
    python export_trees_geojson.py --site almaty --size 1000

Outputs -> public/heatmaps/<site>[/1km]/trees.geojson
"""

import argparse
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from collections import defaultdict
from sites import SITES

ANALYSIS_DIR = Path(__file__).parent
PUBLIC_DIR   = ANALYSIS_DIR.parent / "public"

# Crown radius estimation
DEFAULT_CROWN_RADIUS = 4.0   # metres — typical urban tree
HEIGHT_TO_CROWN      = 0.4   # allometric: crown_radius ≈ height * 0.4
CIRCLE_SEGMENTS      = 24    # vertices per circular canopy polygon


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _circle_polygon(lon_c, lat_c, radius_m, n=CIRCLE_SEGMENTS):
    """Generate a GeoJSON polygon ring (circle) around a point."""
    ring = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        dlat = (radius_m * math.cos(angle)) / 111_320
        dlon = (radius_m * math.sin(angle)) / (111_320 * math.cos(math.radians(lat_c)))
        ring.append([round(lon_c + dlon, 7), round(lat_c + dlat, 7)])
    ring.append(ring[0])  # close
    return ring


def _bbox(ring):
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (min(lons), min(lats), max(lons), max(lats))


def _bbox_area(b):
    return (b[2] - b[0]) * (b[3] - b[1])


def _bbox_contains(outer, inner):
    return (inner[0] >= outer[0] and inner[1] >= outer[1] and
            inner[2] <= outer[2] and inner[3] <= outer[3])


# ---------------------------------------------------------------------------
# Source 1: OSM tree points -> circular canopy polygons
# ---------------------------------------------------------------------------

def _extract_osm_trees(vegetation):
    """Convert OSM tree point features to canopy circle polygons."""
    features = []
    for tid, tree in vegetation.items():
        geom = tree.get("geometry", {})
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]

        props = tree.get("properties", {})
        crown_r = DEFAULT_CROWN_RADIUS
        if props.get("diameter_crown"):
            try:
                crown_r = float(props["diameter_crown"]) / 2
            except (TypeError, ValueError):
                pass
        elif props.get("crown_radius"):
            try:
                crown_r = float(props["crown_radius"])
            except (TypeError, ValueError):
                pass
        elif props.get("height"):
            try:
                crown_r = max(float(props["height"]) * HEIGHT_TO_CROWN, 2.0)
            except (TypeError, ValueError):
                pass

        ring = _circle_polygon(lon, lat, crown_r)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "id": tid,
                "source": "osm",
                "kind": "tree",
                "crown_radius": round(crown_r, 1),
            },
        })
    return features


# ---------------------------------------------------------------------------
# Source 2: Ground-material vegetation polygons (parks/woods/grass)
# ---------------------------------------------------------------------------

def _simplify_ring(ring, tolerance_deg=0.00005):
    """Ramer-Douglas-Peucker simplification for a GeoJSON ring."""
    if len(ring) <= 4:
        return ring

    def _perp_dist(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    def _rdp(pts, eps):
        if len(pts) <= 2:
            return pts
        dmax, idx = 0, 0
        for i in range(1, len(pts) - 1):
            d = _perp_dist(pts[i], pts[0], pts[-1])
            if d > dmax:
                dmax = d
                idx = i
        if dmax > eps:
            left = _rdp(pts[:idx + 1], eps)
            right = _rdp(pts[idx:], eps)
            return left[:-1] + right
        return [pts[0], pts[-1]]

    # Don't simplify the closing vertex
    simplified = _rdp(ring[:-1], tolerance_deg)
    if len(simplified) < 3:
        return ring  # too few points, keep original
    simplified.append(simplified[0])  # re-close
    return simplified


def _extract_ground_vegetation(ground_materials):
    """Extract and simplify vegetation zone polygons from ground_materials."""
    veg_fc = ground_materials.get("vegetation", {})
    raw_feats = veg_fc.get("features", [])
    features = []

    for feat in raw_feats:
        props = feat.get("properties", {})
        cls = props.get("class", "")
        typ = props.get("type", "")
        if cls not in ("wood", "park", "grass") and typ not in ("forest", "grass", "wood", "park", "grassland"):
            continue

        geom = feat.get("geometry", {})
        geom_type = geom.get("type")
        kind = cls or typ

        if geom_type == "Polygon":
            coords = [_simplify_ring([[p[0], p[1]] for p in ring]) for ring in geom["coordinates"]]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": coords},
                "properties": {"id": f"gm_{feat.get('id', len(features))}", "source": "ground", "kind": kind},
            })
        elif geom_type == "MultiPolygon":
            for pi, polygon in enumerate(geom["coordinates"]):
                coords = [_simplify_ring([[p[0], p[1]] for p in ring]) for ring in polygon]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": coords},
                    "properties": {"id": f"gm_{feat.get('id', len(features))}_{pi}", "source": "ground", "kind": kind},
                })
    return features


# ---------------------------------------------------------------------------
# Source 3: OSM Overpass — tree_rows, parks, forests not in ground_materials
# ---------------------------------------------------------------------------

OVERPASS_VEG_CACHE = ANALYSIS_DIR / "cache" / "osm_vegetation"
TREE_ROW_BUFFER_M  = 3.0  # buffer half-width for tree_row lines


def _fetch_osm_vegetation(site_key, lat_c, lon_c, size=500):
    """Fetch vegetation polygons + tree_rows from OSM Overpass. Cached."""
    cache_file = OVERPASS_VEG_CACHE / f"{site_key}_{size}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
        print(f"    [osm veg] {len(cached)} from cache")
        return cached

    half_m = size / 2 + 50
    half_lat = half_m / 111_320
    half_lon = half_m / (111_320 * math.cos(math.radians(lat_c)))
    bbox = f"({lat_c - half_lat},{lon_c - half_lon},{lat_c + half_lat},{lon_c + half_lon})"

    query = (
        '[out:json][timeout:30];('
        f'way["natural"~"^(tree_row|wood|scrub|grassland)$"]{bbox};'
        f'way["landuse"~"^(forest|grass|meadow|orchard|flowerbed)$"]{bbox};'
        f'way["leisure"~"^(park|garden)$"]{bbox};'
        f'relation["leisure"~"^(park|garden)$"]{bbox};'
        f'relation["landuse"~"^(forest|grass|meadow)$"]{bbox};'
        ');out geom;'
    )
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)

    print(f"    [osm veg] fetching Overpass vegetation for {site_key}/{size}m ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "infrared-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"    [osm veg] fetch failed: {exc}")
        return []

    features = []
    buf_lat = TREE_ROW_BUFFER_M / 111_320
    buf_lon = TREE_ROW_BUFFER_M / (111_320 * math.cos(math.radians(lat_c)))
    buf_deg = (buf_lat + buf_lon) / 2

    for el in data.get("elements", []):
        tags = el.get("tags", {})
        kind = (tags.get("natural") or tags.get("landuse") or
                tags.get("leisure") or "vegetation")

        if el["type"] == "way" and el.get("geometry"):
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) < 2:
                continue

            # Closed way -> polygon; open way (tree_row) -> buffered line
            is_closed = (len(coords) >= 4 and
                         abs(coords[0][0] - coords[-1][0]) < 1e-8 and
                         abs(coords[0][1] - coords[-1][1]) < 1e-8)

            if is_closed:
                ring = [[round(c[0], 7), round(c[1], 7)] for c in coords]
                ring = _simplify_ring(ring)
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                    "properties": {"id": f"ov_{el['id']}", "source": "osm_overpass", "kind": kind},
                })
            else:
                # tree_row or open way -> buffer to polygon
                try:
                    from shapely.geometry import LineString
                    line = LineString(coords)
                    buffered = line.buffer(buf_deg, resolution=4)
                    if not buffered.is_empty:
                        ring = [[round(c[0], 7), round(c[1], 7)] for c in buffered.exterior.coords]
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "Polygon", "coordinates": [ring]},
                            "properties": {"id": f"ov_{el['id']}", "source": "osm_overpass", "kind": kind},
                        })
                except Exception:
                    pass

        elif el["type"] == "relation" and el.get("members"):
            for mi, m in enumerate(el["members"]):
                if m.get("type") == "way" and m.get("role") == "outer" and m.get("geometry"):
                    coords = [(p["lon"], p["lat"]) for p in m["geometry"]]
                    if len(coords) < 4:
                        continue
                    ring = [[round(c[0], 7), round(c[1], 7)] for c in coords]
                    ring = _simplify_ring(ring)
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": [ring]},
                        "properties": {"id": f"ov_{el['id']}_{mi}", "source": "osm_overpass", "kind": kind},
                    })

    # Cache
    OVERPASS_VEG_CACHE.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(features, f)
    print(f"    [osm veg] {len(features)} features fetched, cached")

    return features


# ---------------------------------------------------------------------------
# Containment removal
# ---------------------------------------------------------------------------

class SpatialGrid:
    def __init__(self, cell_deg=0.001):
        self.cell = cell_deg
        self.grid = defaultdict(list)

    def _key(self, lon, lat):
        return (int(lon / self.cell), int(lat / self.cell))

    def insert(self, idx, bbox):
        x0, y0 = self._key(bbox[0], bbox[1])
        x1, y1 = self._key(bbox[2], bbox[3])
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                self.grid[(gx, gy)].append(idx)

    def query(self, bbox):
        x0, y0 = self._key(bbox[0], bbox[1])
        x1, y1 = self._key(bbox[2], bbox[3])
        hits = set()
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                for idx in self.grid.get((gx, gy), []):
                    hits.add(idx)
        return hits


def _remove_contained(features):
    """Remove smaller polygons fully contained inside larger ones."""
    n = len(features)
    if n < 2:
        return features

    bboxes = [_bbox(f["geometry"]["coordinates"][0]) for f in features]
    areas = [_bbox_area(b) for b in bboxes]

    grid = SpatialGrid(cell_deg=0.001)
    for i in range(n):
        grid.insert(i, bboxes[i])

    indexed = sorted(range(n), key=lambda i: areas[i], reverse=True)
    removed = set()

    for i in indexed:
        if i in removed:
            continue
        for j in grid.query(bboxes[i]):
            if j == i or j in removed:
                continue
            if areas[j] < areas[i] and _bbox_contains(bboxes[i], bboxes[j]):
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
# Building subtraction: clip trees by building footprints
# ---------------------------------------------------------------------------

def _subtract_buildings(features, bldg_path):
    """Subtract building polygons from tree polygons where they overlap."""
    if not bldg_path.exists():
        return features

    from shapely.geometry import shape, mapping, Polygon as ShapelyPolygon, MultiPolygon
    from shapely.strtree import STRtree
    from shapely.validation import make_valid

    with open(bldg_path) as f:
        bldg_data = json.load(f)

    bldg_feats = bldg_data.get("features", [])
    if not bldg_feats:
        return features

    # Build shapely polygons for buildings
    bldg_polys = []
    for bf in bldg_feats:
        try:
            p = shape(bf["geometry"])
            if not p.is_valid:
                p = make_valid(p)
            if not p.is_empty:
                bldg_polys.append(p)
        except Exception:
            continue

    if not bldg_polys:
        return features

    bldg_tree = STRtree(bldg_polys)

    result = []
    clipped = 0
    removed = 0

    for feat in features:
        try:
            tree_poly = shape(feat["geometry"])
            if not tree_poly.is_valid:
                tree_poly = make_valid(tree_poly)
        except Exception:
            result.append(feat)
            continue

        # Find overlapping buildings
        hits = bldg_tree.query(tree_poly)
        if len(hits) == 0:
            result.append(feat)
            continue

        # Subtract all overlapping buildings
        clipped_poly = tree_poly
        for idx in hits:
            try:
                clipped_poly = clipped_poly.difference(bldg_polys[idx])
            except Exception:
                continue

        if clipped_poly.is_empty:
            removed += 1
            continue

        # Convert back to GeoJSON feature(s)
        if isinstance(clipped_poly, MultiPolygon):
            for pi, part in enumerate(clipped_poly.geoms):
                if part.is_empty or part.area < 1e-12:
                    continue
                coords = [[[round(c[0], 7), round(c[1], 7)] for c in part.exterior.coords]]
                new_feat = {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": coords},
                    "properties": dict(feat["properties"]),
                }
                new_feat["properties"]["id"] = f"{feat['properties']['id']}_{pi}"
                result.append(new_feat)
                clipped += 1
        elif isinstance(clipped_poly, ShapelyPolygon):
            if clipped_poly.area < 1e-12:
                removed += 1
                continue
            coords = [[[round(c[0], 7), round(c[1], 7)] for c in clipped_poly.exterior.coords]]
            new_feat = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": coords},
                "properties": dict(feat["properties"]),
            }
            if clipped_poly.area < tree_poly.area * 0.99:
                clipped += 1
            result.append(new_feat)
        else:
            # GeometryCollection or other — skip tiny fragments
            for geom in getattr(clipped_poly, 'geoms', []):
                if isinstance(geom, ShapelyPolygon) and geom.area >= 1e-12:
                    coords = [[[round(c[0], 7), round(c[1], 7)] for c in geom.exterior.coords]]
                    new_feat = {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": coords},
                        "properties": dict(feat["properties"]),
                    }
                    result.append(new_feat)
                    clipped += 1

    if clipped or removed:
        print(f"    building clip: {clipped} clipped, {removed} fully inside buildings")

    return result


# ---------------------------------------------------------------------------
# Merge overlapping tree polygons
# ---------------------------------------------------------------------------

def _merge_overlapping(features):
    """Merge overlapping tree polygons using unary_union."""
    if len(features) < 2:
        return features

    from shapely.geometry import shape, Polygon as ShapelyPolygon, MultiPolygon
    from shapely.ops import unary_union
    from shapely.validation import make_valid

    polys = []
    for f in features:
        try:
            p = shape(f["geometry"])
            if not p.is_valid:
                p = make_valid(p)
            if not p.is_empty and isinstance(p, ShapelyPolygon):
                polys.append(p)
        except Exception:
            continue

    if not polys:
        return features

    merged = unary_union(polys)
    if merged.is_empty:
        return []

    # Explode back to individual polygons
    if isinstance(merged, ShapelyPolygon):
        parts = [merged]
    elif isinstance(merged, MultiPolygon):
        parts = list(merged.geoms)
    else:
        parts = [g for g in getattr(merged, 'geoms', []) if isinstance(g, ShapelyPolygon)]

    # Minimum area filter — drop slivers (< ~1 m² in degree space)
    min_area = 1e-10
    result = []
    for i, poly in enumerate(parts):
        if poly.is_empty or poly.area < min_area:
            continue
        coords = [[[round(c[0], 7), round(c[1], 7)] for c in poly.exterior.coords]]
        # Classify by area: small = individual tree canopy, large = zone
        area_m2 = poly.area * (111_320 ** 2)  # rough conversion
        source = "osm" if area_m2 < 200 else "ground"
        kind = "tree" if source == "osm" else "zone"
        result.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": {"id": f"m_{i}", "source": source, "kind": kind},
        })

    before = len(features)
    print(f"    merge: {before} -> {len(result)} (merged overlapping polygons)")
    return result


# ---------------------------------------------------------------------------
# Road subtraction: fetch OSM roads, buffer, subtract from trees
# ---------------------------------------------------------------------------

# Half-widths in metres per OSM highway type (conservative — just the pavement)
ROAD_WIDTHS = {
    "motorway": 10, "motorway_link": 6,
    "trunk": 8, "trunk_link": 5,
    "primary": 6, "primary_link": 4,
    "secondary": 5, "secondary_link": 3.5,
    "tertiary": 4, "tertiary_link": 3,
    "residential": 3, "living_street": 2.5,
    "unclassified": 3, "service": 2.5,
}

ROAD_CACHE_DIR = ANALYSIS_DIR / "cache" / "roads"


def _fetch_roads(lat_c, lon_c, size, site_key):
    """Fetch OSM road centerlines and buffer to road polygons. Cached."""
    cache_file = ROAD_CACHE_DIR / f"{site_key}_{size}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    half_m = size / 2 + 100
    half_lat = half_m / 111_320
    half_lon = half_m / (111_320 * math.cos(math.radians(lat_c)))
    bbox = f"{lat_c - half_lat},{lon_c - half_lon},{lat_c + half_lat},{lon_c + half_lon}"

    highway_types = "|".join(ROAD_WIDTHS.keys())
    query = (
        f'[out:json][timeout:30];'
        f'way["highway"~"^({highway_types})$"]({bbox});'
        f'out geom;'
    )
    url = f"https://overpass-api.de/api/interpreter?data={urllib.parse.quote(query)}"

    print(f"    [roads] fetching OSM highways for {site_key}/{size}m ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "infrared-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"    [roads] fetch failed: {exc}")
        return []

    # Buffer each road centerline to a polygon
    from shapely.geometry import LineString, Polygon as ShapelyPolygon, MultiPolygon
    from shapely.ops import unary_union

    road_polys = []
    for el in data.get("elements", []):
        if el.get("type") != "way" or not el.get("geometry"):
            continue
        hw_type = el.get("tags", {}).get("highway", "")
        half_w = ROAD_WIDTHS.get(hw_type, 5)
        # Convert half-width to degrees (approximate)
        buf_lat = half_w / 111_320
        buf_lon = half_w / (111_320 * math.cos(math.radians(lat_c)))
        buf_deg = (buf_lat + buf_lon) / 2  # average for simplicity

        coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
        if len(coords) < 2:
            continue
        try:
            line = LineString(coords)
            buffered = line.buffer(buf_deg, resolution=4)
            if not buffered.is_empty:
                road_polys.append(buffered)
        except Exception:
            continue

    if not road_polys:
        print(f"    [roads] no roads found")
        return []

    # Keep individual road buffer polygons (do NOT unary_union — they'd merge into one blob)
    road_features = []
    for poly in road_polys:
        if poly.is_empty:
            continue
        if isinstance(poly, ShapelyPolygon):
            ring = [[round(c[0], 7), round(c[1], 7)] for c in poly.exterior.coords]
            road_features.append(ring)
        elif isinstance(poly, MultiPolygon):
            for part in poly.geoms:
                if not part.is_empty:
                    ring = [[round(c[0], 7), round(c[1], 7)] for c in part.exterior.coords]
                    road_features.append(ring)

    # Cache
    ROAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(road_features, f)
    print(f"    [roads] {len(data.get('elements', []))} ways -> {len(road_features)} road polygons, cached")

    return road_features


def _subtract_roads(features, road_rings):
    """Subtract road polygons from tree polygons."""
    if not road_rings:
        return features

    from shapely.geometry import shape, Polygon as ShapelyPolygon, MultiPolygon
    from shapely.strtree import STRtree
    from shapely.validation import make_valid

    road_polys = []
    for ring in road_rings:
        try:
            p = ShapelyPolygon(ring)
            if p.is_valid and not p.is_empty:
                road_polys.append(p)
        except Exception:
            continue

    if not road_polys:
        return features

    road_tree = STRtree(road_polys)

    result = []
    clipped = 0
    removed = 0

    for feat in features:
        try:
            tree_poly = shape(feat["geometry"])
            if not tree_poly.is_valid:
                tree_poly = make_valid(tree_poly)
        except Exception:
            result.append(feat)
            continue

        hits = road_tree.query(tree_poly)
        if len(hits) == 0:
            result.append(feat)
            continue

        clipped_poly = tree_poly
        for idx in hits:
            try:
                clipped_poly = clipped_poly.difference(road_polys[idx])
            except Exception:
                continue

        if clipped_poly.is_empty:
            removed += 1
            continue

        # Convert result back to GeoJSON
        if isinstance(clipped_poly, MultiPolygon):
            for pi, part in enumerate(clipped_poly.geoms):
                if part.is_empty or part.area < 1e-12:
                    continue
                coords = [[[round(c[0], 7), round(c[1], 7)] for c in part.exterior.coords]]
                new_feat = {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": coords},
                    "properties": dict(feat["properties"]),
                }
                new_feat["properties"]["id"] = f"{feat['properties']['id']}_r{pi}"
                result.append(new_feat)
                clipped += 1
        elif isinstance(clipped_poly, ShapelyPolygon):
            if clipped_poly.area < 1e-12:
                removed += 1
                continue
            coords = [[[round(c[0], 7), round(c[1], 7)] for c in clipped_poly.exterior.coords]]
            new_feat = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": coords},
                "properties": dict(feat["properties"]),
            }
            if clipped_poly.area < tree_poly.area * 0.99:
                clipped += 1
            result.append(new_feat)
        else:
            for geom in getattr(clipped_poly, 'geoms', []):
                if isinstance(geom, ShapelyPolygon) and geom.area >= 1e-12:
                    coords = [[[round(c[0], 7), round(c[1], 7)] for c in geom.exterior.coords]]
                    new_feat = {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": coords},
                        "properties": dict(feat["properties"]),
                    }
                    result.append(new_feat)
                    clipped += 1

    if clipped or removed:
        print(f"    road clip: {clipped} clipped, {removed} fully on roads")

    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_site(site_key, size=500):
    site = SITES[site_key]
    subdir = "1km" if size == 1000 else ""
    src_dir = ANALYSIS_DIR / "results" / site_key / (subdir or ".")
    dst_dir = PUBLIC_DIR / "heatmaps" / site_key / (subdir or ".")

    fetched_path = src_dir / "fetched_data.json"
    if not fetched_path.exists():
        print(f"  [{site_key}/{subdir or '500m'}] no fetched_data.json — skipped")
        return 0

    with open(fetched_path) as f:
        data = json.load(f)

    all_features = []

    # Source 1: OSM tree points -> canopy circles
    vegetation = data.get("vegetation", {})
    osm_trees = _extract_osm_trees(vegetation)
    all_features.extend(osm_trees)

    # Source 2: Ground-material vegetation zones (simplified)
    ground_mats = data.get("ground_materials", {})
    gm_veg = _extract_ground_vegetation(ground_mats)
    all_features.extend(gm_veg)

    # Source 3: OSM Overpass — tree_rows, parks, forests
    osm_veg = _fetch_osm_vegetation(site_key, site["lat"], site["lon"], size)
    all_features.extend(osm_veg)

    # Remove small canopies contained inside larger zone polygons
    if all_features:
        all_features = _remove_contained(all_features)

    # Merge overlapping tree polygons
    if all_features:
        all_features = _merge_overlapping(all_features)

    # Subtract building footprints from tree polygons
    bldg_path = dst_dir / "buildings.geojson"
    if all_features:
        all_features = _subtract_buildings(all_features, bldg_path)

    # Subtract road surfaces from tree polygons
    if all_features:
        road_rings = _fetch_roads(site["lat"], site["lon"], size, site_key)
        all_features = _subtract_roads(all_features, road_rings)

    # Drop tiny slivers from clipping (< 10 m2)
    if all_features:
        from shapely.geometry import shape as _sh
        before_sliver = len(all_features)
        all_features = [f for f in all_features
                        if _sh(f["geometry"]).area * (111_320 ** 2) > 10]
        dropped = before_sliver - len(all_features)
        if dropped:
            print(f"    dropped {dropped} slivers (< 10 m2)")

    # Save frontend GeoJSON
    dst_dir.mkdir(parents=True, exist_ok=True)
    geojson = {"type": "FeatureCollection", "features": all_features}
    out_path = dst_dir / "trees.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)

    # Save sim_vegetation.json — SDK-compatible Point features for simulation
    # Each tree polygon -> centroid Point with height + crown_radius
    sim_veg = {}
    for i, feat in enumerate(all_features):
        ring = feat["geometry"]["coordinates"][0]
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        # Estimate crown radius from polygon area
        area_deg2 = abs(sum(
            (ring[j][0] - ring[0][0]) * (ring[(j+1) % len(ring)][1] - ring[0][1]) -
            (ring[(j+1) % len(ring)][0] - ring[0][0]) * (ring[j][1] - ring[0][1])
            for j in range(len(ring))
        ) / 2)
        area_m2 = area_deg2 * (111_320 ** 2) * math.cos(math.radians(cy))
        crown_r = max(2.0, min(20.0, math.sqrt(area_m2 / math.pi)))
        # Use stored crown_radius for individual trees if available
        props = feat.get("properties", {})
        if props.get("crown_radius"):
            crown_r = props["crown_radius"]
        height = max(6.0, crown_r / HEIGHT_TO_CROWN) if props.get("kind") == "tree" else 8.0
        sim_veg[f"tv_{i:04d}"] = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(cx, 7), round(cy, 7)]},
            "properties": {"height": round(height, 1), "crown_radius": round(crown_r, 1)},
        }
    sim_veg_path = src_dir / "sim_vegetation.json"
    with open(sim_veg_path, "w") as f:
        json.dump(sim_veg, f)
    print(f"    saved {len(sim_veg)} SDK vegetation points -> {sim_veg_path.name}")

    n_osm = sum(1 for f in all_features if f["properties"]["source"] == "osm")
    n_gm  = sum(1 for f in all_features if f["properties"]["source"] == "ground")
    n_ov  = sum(1 for f in all_features if f["properties"]["source"] == "osm_overpass")
    tag = f"{site_key}/1km" if size == 1000 else site_key
    parts = []
    if n_osm: parts.append(f"{n_osm} trees")
    if n_gm:  parts.append(f"{n_gm} ground")
    if n_ov:  parts.append(f"{n_ov} overpass")
    print(f"  [{tag}] {len(all_features)} total ({' + '.join(parts) if parts else 'none'})")
    return len(all_features)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()), default=None)
    parser.add_argument("--size", type=int, choices=[500, 1000], default=None)
    args = parser.parse_args()

    print("\n=== Exporting tree canopy GeoJSON ===")

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
