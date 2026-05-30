"""
fetch_overture.py — Overture Maps building enrichment
======================================================
Fetches building footprints from Overture Maps for a site's 1 500 m context
polygon, deduplicates against the OSM / Infrared SDK set, and returns a
merged {id: DotBimMesh} dict ready for run_area() calls.

Install dependencies:
    pip install overturemaps shapely

Usage (called from baseline.py):
    from fetch_overture import enrich_buildings
    buildings = enrich_buildings(site, area.buildings)
"""

import math
import json
from typing import Dict, List, Tuple, Optional

from infrared_sdk.buildings.types import DotBimMesh

# ── Optional dependencies ────────────────────────────────────────────────────
try:
    import overturemaps
    HAS_OVERTURE = True
except ImportError:
    HAS_OVERTURE = False

try:
    from shapely.geometry import Polygon, MultiPolygon, shape
    from shapely.strtree import STRtree
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

try:
    from shapely import from_wkb
    HAS_FROM_WKB = True
except ImportError:
    try:
        from shapely.wkb import loads as from_wkb
        HAS_FROM_WKB = True
    except ImportError:
        HAS_FROM_WKB = False

# ── Tunables ─────────────────────────────────────────────────────────────────
DEFAULT_HEIGHT    = 9.0    # m — fallback when Overture lacks height data
FLOORS_TO_HEIGHT  = 3.2    # m per floor
IOU_THRESHOLD     = 0.25   # overlap fraction above which → considered a duplicate
OVERTURE_ID_START = 90_000 # base mesh_id for Overture buildings (avoids OSM clash)


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _analysis_sw(lat_c: float, lon_c: float) -> Tuple[float, float]:
    """SW corner of the 500 m analysis polygon — origin of the local coord system."""
    half_lat = 250 / 111_320
    half_lon = 250 / (111_320 * math.cos(math.radians(lat_c)))
    return lat_c - half_lat, lon_c - half_lon


def _to_local(lat: float, lon: float,
              orig_lat: float, orig_lon: float) -> Tuple[float, float]:
    """WGS84 → local metres from the analysis-polygon SW corner."""
    x = (lon - orig_lon) * 111_320 * math.cos(math.radians(orig_lat))
    y = (lat - orig_lat) * 111_320
    return x, y


def _context_bbox(lat_c: float, lon_c: float) -> Tuple[float, float, float, float]:
    """(west, south, east, north) bounding box for the 1 500 m context polygon."""
    half_lat = 750 / 111_320
    half_lon = 750 / (111_320 * math.cos(math.radians(lat_c)))
    return (lon_c - half_lon, lat_c - half_lat,
            lon_c + half_lon, lat_c + half_lat)


# ── DotBimMesh builders ───────────────────────────────────────────────────────

def _box_mesh(x0: float, y0: float, x1: float, y1: float,
              height: float, mesh_id: int) -> DotBimMesh:
    """Closed axis-aligned box from bounding rectangle + height."""
    h = max(height, 1.0)
    coords = [
        x0, y0, 0.0,    x1, y0, 0.0,    x1, y1, 0.0,    x0, y1, 0.0,
        x0, y0, h,      x1, y0, h,      x1, y1, h,      x0, y1, h,
    ]
    indices = [
        0, 2, 1,  0, 3, 2,     # bottom
        4, 5, 6,  4, 6, 7,     # top
        0, 1, 5,  0, 5, 4,     # south wall
        2, 3, 7,  2, 7, 6,     # north wall
        3, 0, 4,  3, 4, 7,     # west wall
        1, 2, 6,  1, 6, 5,     # east wall
    ]
    return DotBimMesh(mesh_id=mesh_id, coordinates=coords, indices=indices)


def _poly_mesh(ring_lonlat: List[Tuple[float, float]],
               height: float, mesh_id: int,
               orig_lat: float, orig_lon: float) -> DotBimMesh:
    """
    Extrude a closed polygon ring (WGS84 lon/lat) to a triangulated 3-D mesh.
    Uses a fan triangulation from vertex 0 — accurate for convex footprints,
    good enough for the mild concavities of most building outlines.
    Falls back to the bounding-box mesh on any error.
    """
    try:
        # Drop repeated closing vertex; convert to local metres
        pts = [_to_local(lat, lon, orig_lat, orig_lon)
               for (lon, lat) in ring_lonlat[:-1]]
        n = len(pts)
        if n < 3:
            raise ValueError("degenerate polygon")

        h = max(height, 1.0)
        # Vertex list: bottom ring (z=0) followed by top ring (z=h)
        coords: List[float] = []
        for (x, y) in pts:
            coords += [x, y, 0.0]
        for (x, y) in pts:
            coords += [x, y, h]

        indices: List[int] = []
        # Bottom face — fan, reversed winding → outward normal points DOWN
        for i in range(1, n - 1):
            indices += [0, i + 1, i]
        # Top face — fan, normal points UP
        for i in range(1, n - 1):
            indices += [n, n + i, n + i + 1]
        # Side walls — one quad (two triangles) per edge
        for i in range(n):
            j = (i + 1) % n
            indices += [i, j, n + j,  i, n + j, n + i]

        return DotBimMesh(mesh_id=mesh_id, coordinates=coords, indices=indices)

    except Exception:
        # Graceful fallback: axis-aligned bounding box
        xs = [_to_local(lat, lon, orig_lat, orig_lon)[0]
              for (lon, lat) in ring_lonlat]
        ys = [_to_local(lat, lon, orig_lat, orig_lon)[1]
              for (lon, lat) in ring_lonlat]
        return _box_mesh(min(xs), min(ys), max(xs), max(ys), height, mesh_id)


# ── Spatial deduplication ─────────────────────────────────────────────────────

def _osm_footprints(osm_buildings: Dict) -> List[Polygon]:
    """
    Reconstruct approximate bounding-box Shapely polygons from DotBimMesh
    vertex data.  Used only for overlap detection, not for rendering.
    """
    polys: List[Polygon] = []
    for mesh in osm_buildings.values():
        coords = mesh.coordinates        # flat [x, y, z, x, y, z, …]
        xs = coords[0::3]
        ys = coords[1::3]
        if len(xs) < 3:
            continue
        polys.append(Polygon([
            (min(xs), min(ys)), (max(xs), min(ys)),
            (max(xs), max(ys)), (min(xs), max(ys)),
        ]))
    return polys


def _is_duplicate(over_local: Polygon,
                  osm_tree: "STRtree",
                  osm_polys: List[Polygon]) -> bool:
    """Return True if over_local overlaps any OSM building beyond IOU_THRESHOLD."""
    for idx in osm_tree.query(over_local):
        osm = osm_polys[idx]
        try:
            inter = over_local.intersection(osm).area
            if inter <= 0:
                continue
            iou = inter / over_local.union(osm).area
            if iou >= IOU_THRESHOLD:
                return True
            if osm.contains(over_local.centroid):
                return True
        except Exception:
            continue
    return False


# ── Public API ────────────────────────────────────────────────────────────────

def enrich_buildings(site: dict, osm_buildings: Dict) -> Dict:
    """
    Return osm_buildings enriched with non-duplicate Overture Maps buildings.

    Parameters
    ----------
    site          : SITES[key] dict from sites.py
    osm_buildings : {id: DotBimMesh} from InfraredClient.buildings.get_area()

    Returns
    -------
    Merged {id: DotBimMesh} — a strict superset of osm_buildings.
    Falls back to osm_buildings unchanged if prerequisites are missing or the
    Overture fetch fails.
    """
    if not HAS_OVERTURE:
        print("  [overture] skipped — run: pip install overturemaps")
        return osm_buildings
    if not HAS_SHAPELY:
        print("  [overture] skipped — run: pip install shapely")
        return osm_buildings
    if not HAS_FROM_WKB:
        print("  [overture] skipped — shapely WKB parser not available")
        return osm_buildings

    lat_c, lon_c       = site["lat"], site["lon"]
    orig_lat, orig_lon = _analysis_sw(lat_c, lon_c)
    bbox               = _context_bbox(lat_c, lon_c)   # (W, S, E, N)

    print(f"  [overture] bbox ({bbox[0]:.4f}, {bbox[1]:.4f}, "
          f"{bbox[2]:.4f}, {bbox[3]:.4f}) ...")
    try:
        table = overturemaps.record_batch_reader("building", bbox=bbox).read_all()
    except Exception as exc:
        print(f"  [overture] fetch failed ({exc}) — using OSM only")
        return osm_buildings

    n_over = len(table)
    print(f"  [overture] {n_over} Overture buildings returned")
    if n_over == 0:
        return osm_buildings

    # Build OSM spatial index in local metres
    osm_polys = _osm_footprints(osm_buildings)
    osm_tree  = STRtree(osm_polys)

    # Column handles
    schema_names = table.schema.names
    geom_col     = table.column("geometry")
    height_col   = table.column("height")     if "height"     in schema_names else None
    floors_col   = table.column("num_floors") if "num_floors" in schema_names else None

    merged = dict(osm_buildings)
    added  = 0

    for i in range(n_over):
        # ── Geometry ──────────────────────────────────────────────────────
        raw = geom_col[i].as_py()
        if raw is None:
            continue
        try:
            geom = from_wkb(raw) if isinstance(raw, (bytes, bytearray)) \
                   else shape(raw)
        except Exception:
            continue

        # ── Height ────────────────────────────────────────────────────────
        height = DEFAULT_HEIGHT
        if height_col is not None:
            h = height_col[i].as_py()
            if h is not None:
                try:
                    height = max(float(h), 1.0)
                except (TypeError, ValueError):
                    pass
        if height == DEFAULT_HEIGHT and floors_col is not None:
            fl = floors_col[i].as_py()
            if fl is not None:
                try:
                    height = max(float(fl) * FLOORS_TO_HEIGHT, 1.0)
                except (TypeError, ValueError):
                    pass

        # ── Sub-polygons (handle MultiPolygon) ────────────────────────────
        sub_polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]

        for poly in sub_polys:
            if not isinstance(poly, Polygon) or poly.is_empty:
                continue

            ring = list(poly.exterior.coords)

            # Convert to local metres for deduplication
            local_ring = [_to_local(lat, lon, orig_lat, orig_lon)
                          for (lon, lat) in ring]
            local_poly = Polygon(local_ring)

            if _is_duplicate(local_poly, osm_tree, osm_polys):
                continue

            # Build extruded mesh from original WGS84 ring
            mesh = _poly_mesh(ring, height,
                              mesh_id=OVERTURE_ID_START + added,
                              orig_lat=orig_lat, orig_lon=orig_lon)
            merged[f"ov_{added:05d}"] = mesh
            added += 1

    n_osm = len(osm_buildings)
    print(f"  [overture] +{added} new buildings added  "
          f"(OSM: {n_osm} -> total: {len(merged)})")
    return merged
