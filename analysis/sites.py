"""
RenovationMap — site configurations
=====================================
Four sites, one pipeline.

  almaty  →  Medeu/Dostyk Embassy Row      (43.245N, 76.948E)  —  winter cold stress
  riyadh  →  Al-Murabba / Diriyah Gate     (24.692N, 46.709E)  —  summer heat stress
  astana  →  Bayterek / Nurzhol Blvd       (51.128N, 71.430E)  —  steppe cold stress
  mecca   →  Masjid al-Haram surrounds     (21.427N, 39.814E)  —  extreme heat stress

Primary analysis polygons are 500 m × 500 m (study area).
Extended analysis polygons are 1 000 m × 1 000 m (used for 1 km finance models).
"""

# ---------------------------------------------------------------------------
# Polygon helpers
# ---------------------------------------------------------------------------
import math

def _make_polygon(lat_c, lon_c, half_m):
    """Return a square GeoJSON Polygon of side 2*half_m centred on lat_c/lon_c."""
    half_lat = half_m / 111_320
    half_lon = half_m / (111_320 * math.cos(math.radians(lat_c)))
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon_c - half_lon, lat_c - half_lat],   # SW
            [lon_c + half_lon, lat_c - half_lat],   # SE
            [lon_c + half_lon, lat_c + half_lat],   # NE
            [lon_c - half_lon, lat_c + half_lat],   # NW
            [lon_c - half_lon, lat_c - half_lat],   # close
        ]],
    }

def _polygon_500m(lat_c, lon_c):
    """Return a 500 × 500 m GeoJSON Polygon centred on lat_c / lon_c."""
    return _make_polygon(lat_c, lon_c, 250)

def _polygon_1km(lat_c, lon_c):
    """Return a 1 000 × 1 000 m GeoJSON Polygon centred on lat_c / lon_c."""
    return _make_polygon(lat_c, lon_c, 500)

def _polygon_context(lat_c, lon_c, size_m=1500):
    """
    Return a wider context polygon (default 1 500 m) for building & vegetation
    fetch.  Surrounding urban morphology (wind channelling, solar shadowing) is
    captured even though the analysis *output* stays at the inner 1 km grid.
    """
    half_lat = (size_m / 2) / 111_320
    half_lon = (size_m / 2) / (111_320 * math.cos(math.radians(lat_c)))
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon_c - half_lon, lat_c - half_lat],
            [lon_c + half_lon, lat_c - half_lat],
            [lon_c + half_lon, lat_c + half_lat],
            [lon_c - half_lon, lat_c + half_lat],
            [lon_c - half_lon, lat_c - half_lat],
        ]],
    }

def _inner_polygon(lat_c, lon_c, size_m=500):
    """Smaller inner polygon (default 500 m) for ground-material override."""
    half_lat = (size_m / 2) / 111_320
    half_lon = (size_m / 2) / (111_320 * math.cos(math.radians(lat_c)))
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [lon_c - half_lon, lat_c - half_lat],
                    [lon_c + half_lon, lat_c - half_lat],
                    [lon_c + half_lon, lat_c + half_lat],
                    [lon_c - half_lon, lat_c + half_lat],
                    [lon_c - half_lon, lat_c - half_lat],
                ]],
            },
            "properties": {},
        }],
    }


# ---------------------------------------------------------------------------
# Site definitions
# ---------------------------------------------------------------------------

SITES = {}

# ── Almaty — Medeu / Dostyk / Embassy Row ───────────────────────────────────
_ALM_LAT, _ALM_LON = 43.2450, 76.9480

# Windbreak: 3 staggered rows of birch trees along the north edge, 8 m apart
# north_m = distance of first row from site centre (sized to polygon half-width - 30m margin)
# 3 rows × ~115 trees @ 10 m height → shelter zone covers ~200 m downwind (920 m wide)
def _almaty_windbreak(north_m=220):
    spacing   = 8 / (111_320 * math.cos(math.radians(_ALM_LAT)))
    row_step  = 8 / 111_320
    half_lon  = 460 / (111_320 * math.cos(math.radians(_ALM_LAT)))
    trees = {}
    i = 0
    for row in range(3):
        lat = _ALM_LAT + (north_m / 111_320) - row * row_step
        lon = _ALM_LON - half_lon
        while lon <= _ALM_LON + half_lon + 1e-9:
            trees[f"wb_{i:03d}"] = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"height": 10, "crown_radius": 3, "genus": "Betula"},
            }
            lon += spacing
            i += 1
    return trees

SITES["almaty"] = {
    "name":            "Almaty — Medeu/Dostyk Embassy Row",
    "lat":             _ALM_LAT,
    "lon":             _ALM_LON,
    "polygon":         _polygon_500m(_ALM_LAT, _ALM_LON),
    "polygon_1km":     _polygon_1km(_ALM_LAT, _ALM_LON),
    "context_polygon": _polygon_context(_ALM_LAT, _ALM_LON),
    "climate":         "cold",
    "weather_radius":  150,

    # Analyses
    "wind_direction":  0,            # FROM north (Siberian anticyclone)
    "wind_speed":      10,
    "wind_label":      "N-wind (Siberian), 10 m/s",

    # Single-month windows (server requirement)
    "solar_month":     12,           # December — worst solar access
    "solar_hours":     (9, 15),
    "utci_month":      1,            # January — coldest
    "utci_hours":      (9, 15),

    "solar_analysis":  "direct_sun_hours",   # geometry-only, no weather
    "solar_unit":      "hrs/day",
    "solar_cmap":      "plasma",

    # Scoring (cold climate — lower is worse)
    "score_config": {
        "wind_label":   "Wind trap",
        "wind_metric":  "frac_gt5ms",
        "wind_bad":     ">5 m/s = cold discomfort",
        "wind_worst":   0.60, "wind_best": 0.05,
        "wind_weight":  0.35,

        "solar_label":  "Solar deficit",
        "solar_metric": "frac_lt1h",
        "solar_bad":    "<1 h sun/day in December",
        "solar_worst":  0.80, "solar_best": 0.10,
        "solar_weight": 0.35,

        "utci_label":   "Cold stress",
        "utci_metric":  "frac_utci_bad",
        "utci_bad":     "UTCI < -13 C (moderate cold stress, January)",
        "utci_worst":   0.90, "utci_best": 0.20,
        "utci_weight":  0.30,
        "utci_thresh":  -13,
        "utci_bad_dir": "below",    # bad = below threshold
    },

    # Scenarios (500 m polygon — trees placed 220 m from centre, inside 250 m half-edge)
    "scenario_A": {
        "label":       "Windbreak birch trees (3-row, N edge, 920 m wide)",
        "tree_fn":     lambda: _almaty_windbreak(north_m=220),
        "tree_fn_1km": lambda: _almaty_windbreak(north_m=475),
        "tree_props":  {"height": 10, "crown_radius": 3, "genus": "Betula"},
        "ground_key":  None,
    },
    "scenario_B": {
        "label":       "Asphalt -> grass (courtyard surface)",
        "tree_fn":     None,
        "ground_key":  "vegetation",
        "ground_fc":   _inner_polygon(_ALM_LAT, _ALM_LON, size_m=400),
    },
    "scenario_C_label": "3-row windbreak + grass (combined)",
}


# ── Riyadh — Al-Murabba / Diriyah Gate edge ─────────────────────────────────
_RIY_LAT, _RIY_LON = 24.692222, 46.708835

# Shade trees: grid of date palms across the courtyard interior
def _riyadh_shade_trees():
    """9-row × 57-col grid of date palms — 513 trees, 10 × 10 m spacing, 4 m crown.
    Covers ±40 m N-S and ±280 m E-W of the courtyard centre.
    """
    spacing_lon = 10 / (111_320 * math.cos(math.radians(_RIY_LAT)))
    spacing_lat = 10 / 111_320
    trees = {}
    i = 0
    for row in range(9):                               # 9 rows: -4…+4 relative to centre
        lat = _RIY_LAT + (-4 + row) * spacing_lat
        lon = _RIY_LON - 28 * spacing_lon             # 57 columns (-28…+28)
        while lon <= _RIY_LON + 28 * spacing_lon + 1e-9:
            trees[f"palm_{i:03d}"] = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"height": 12, "crown_radius": 4, "genus": "Phoenix"},
            }
            lon += spacing_lon
            i += 1
    return trees

SITES["riyadh"] = {
    "name":            "Riyadh — Al-Murabba / Diriyah Gate",
    "lat":             _RIY_LAT,
    "lon":             _RIY_LON,
    "polygon":         _polygon_500m(_RIY_LAT, _RIY_LON),
    "polygon_1km":     _polygon_1km(_RIY_LAT, _RIY_LON),
    "context_polygon": _polygon_context(_RIY_LAT, _RIY_LON),
    "climate":         "hot",
    "weather_radius":  100,

    # Analyses
    "wind_direction":       315,     # FROM NW (Shamal wind)
    "wind_speed":           6,
    "wind_label":           "NW Shamal, 6 m/s",
    # directional_blend creates 80% NaN for 315° NW winds (radial falloff leaves
    # the SE corner dead).  Use plain centre-crop for full rectangular coverage.
    "wind_merge_strategy":  "default",

    "solar_month":     7,            # July — peak sun exposure
    "solar_hours":     (7, 17),
    "utci_month":      7,            # July — peak heat
    "utci_hours":      (10, 16),

    "solar_analysis":  "direct_sun_hours",
    "solar_unit":      "hrs/day",
    "solar_cmap":      "hot_r",      # reversed: less sun = better (shade = good)

    # Scoring (hot climate — higher sun/UTCI is worse)
    "score_config": {
        "wind_label":   "Wind stagnation",
        "wind_metric":  "frac_lt1ms",
        "wind_bad":     "<1 m/s = stifling, no evaporative cooling",
        "wind_worst":   0.70, "wind_best": 0.05,
        "wind_weight":  0.20,

        "solar_label":  "Solar overexposure",
        "solar_metric": "frac_gt5h",
        "solar_bad":    ">5 h direct sun/day in July = dangerously exposed",
        "solar_worst":  0.80, "solar_best": 0.10,
        "solar_weight": 0.35,

        "utci_label":   "Heat stress",
        "utci_metric":  "frac_utci_bad",
        "utci_bad":     "UTCI > 38 C (strong heat stress, July)",
        "utci_worst":   0.90, "utci_best": 0.10,
        "utci_weight":  0.45,
        "utci_thresh":  38,
        "utci_bad_dir": "above",    # bad = above threshold
    },

    # Scenarios
    "scenario_A": {
        "label":       "Date palm shade grid (513 trees, courtyard)",
        "tree_fn":     _riyadh_shade_trees,
        "tree_props":  {"height": 12, "crown_radius": 4, "genus": "Phoenix"},
        "ground_key":  None,
    },
    "scenario_B": {
        "label":       "Asphalt -> pale concrete (high-albedo paving)",
        "tree_fn":     None,
        "ground_key":  "concrete",
        "ground_fc":   _inner_polygon(_RIY_LAT, _RIY_LON, size_m=600),
    },
    "scenario_C_label": "513 date palms + pale concrete (combined)",
}


# ── Astana — Bayterek / Nurzhol Blvd ────────────────────────────────────────
_AST_LAT, _AST_LON = 51.160155, 71.406656   # Northern Government Quarter / Ak Bulak Left Bank

# Windbreak: 3 staggered rows of elm trees along the north edge
# north_m = distance of first row from site centre (sized to polygon half-width - 30m margin)
# Steppe site with 12 m/s wind — 3 rows × ~115 trees @ 10 m height
def _astana_windbreak(north_m=220):
    spacing   = 8 / (111_320 * math.cos(math.radians(_AST_LAT)))
    row_step  = 8 / 111_320
    half_lon  = 460 / (111_320 * math.cos(math.radians(_AST_LAT)))
    trees = {}
    i = 0
    for row in range(3):
        lat = _AST_LAT + (north_m / 111_320) - row * row_step
        lon = _AST_LON - half_lon
        while lon <= _AST_LON + half_lon + 1e-9:
            trees[f"wb_{i:03d}"] = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"height": 10, "crown_radius": 3, "genus": "Ulmus"},
            }
            lon += spacing
            i += 1
    return trees

SITES["astana"] = {
    "name":            "Astana — Northern Government Quarter",
    "lat":             _AST_LAT,
    "lon":             _AST_LON,
    "polygon":         _polygon_500m(_AST_LAT, _AST_LON),
    "polygon_1km":     _polygon_1km(_AST_LAT, _AST_LON),
    "context_polygon": _polygon_context(_AST_LAT, _AST_LON),
    "climate":         "cold",
    "weather_radius":  150,

    # Analyses
    "wind_direction":  0,            # FROM north (Siberian anticyclone)
    "wind_speed":      12,           # stronger than Almaty — open steppe
    "wind_label":      "N-wind (steppe), 12 m/s",

    "solar_month":     12,           # December — worst solar access
    "solar_hours":     (9, 15),
    "utci_month":      1,            # January — coldest
    "utci_hours":      (9, 15),

    "solar_analysis":  "direct_sun_hours",
    "solar_unit":      "hrs/day",
    "solar_cmap":      "plasma",

    # Scoring (cold climate)
    "score_config": {
        "wind_label":   "Wind trap",
        "wind_metric":  "frac_gt5ms",
        "wind_bad":     ">5 m/s = cold discomfort",
        "wind_worst":   0.70, "wind_best": 0.05,
        "wind_weight":  0.35,

        "solar_label":  "Solar deficit",
        "solar_metric": "frac_lt1h",
        "solar_bad":    "<1 h sun/day in December",
        "solar_worst":  0.85, "solar_best": 0.10,
        "solar_weight": 0.35,

        "utci_label":   "Cold stress",
        "utci_metric":  "frac_utci_bad",
        "utci_bad":     "UTCI < -13 C (moderate cold stress, January)",
        "utci_worst":   0.95, "utci_best": 0.20,
        "utci_weight":  0.30,
        "utci_thresh":  -13,
        "utci_bad_dir": "below",
    },

    # Scenarios (500 m polygon — trees placed 220 m from centre, inside 250 m half-edge)
    "scenario_A": {
        "label":       "Windbreak elm trees (3-row, N edge, 920 m wide)",
        "tree_fn":     lambda: _astana_windbreak(north_m=220),
        "tree_fn_1km": lambda: _astana_windbreak(north_m=475),
        "tree_props":  {"height": 10, "crown_radius": 3, "genus": "Ulmus"},
        "ground_key":  None,
    },
    "scenario_B": {
        "label":       "Asphalt -> grass (courtyard surface)",
        "tree_fn":     None,
        "ground_key":  "vegetation",
        "ground_fc":   _inner_polygon(_AST_LAT, _AST_LON, size_m=400),
    },
    "scenario_C_label": "3-row windbreak + grass (combined)",
}


# ── Mecca — Masjid al-Haram surrounds ───────────────────────────────────────
_MKK_LAT, _MKK_LON = 21.426522, 39.813546

# Shade trees: grid of date palms covering the main open space
def _mecca_shade_trees():
    """9-row × 57-col grid of date palms — 513 trees, 10 × 10 m spacing, 4 m crown.
    Covers ±40 m N-S and ±280 m E-W of the open-space centre.
    """
    spacing_lon = 10 / (111_320 * math.cos(math.radians(_MKK_LAT)))
    spacing_lat = 10 / 111_320
    trees = {}
    i = 0
    for row in range(9):                               # 9 rows: -4…+4 relative to centre
        lat = _MKK_LAT + (-4 + row) * spacing_lat
        lon = _MKK_LON - 28 * spacing_lon             # 57 columns (-28…+28)
        while lon <= _MKK_LON + 28 * spacing_lon + 1e-9:
            trees[f"palm_{i:03d}"] = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"height": 12, "crown_radius": 4, "genus": "Phoenix"},
            }
            lon += spacing_lon
            i += 1
    return trees

SITES["mecca"] = {
    "name":            "Mecca — Masjid al-Haram surrounds",
    "lat":             _MKK_LAT,
    "lon":             _MKK_LON,
    "polygon":         _polygon_500m(_MKK_LAT, _MKK_LON),
    "polygon_1km":     _polygon_1km(_MKK_LAT, _MKK_LON),
    "context_polygon": _polygon_context(_MKK_LAT, _MKK_LON),
    "climate":         "hot",
    "weather_radius":  100,

    # Analyses
    "wind_direction":  315,          # FROM NW (valley breeze)
    "wind_speed":      4,            # light breeze — sheltered valley site
    "wind_label":      "NW valley breeze, 4 m/s",

    "solar_month":     7,            # July — peak sun exposure
    "solar_hours":     (7, 17),
    "utci_month":      7,            # July — peak heat
    "utci_hours":      (10, 16),

    "solar_analysis":  "direct_sun_hours",
    "solar_unit":      "hrs/day",
    "solar_cmap":      "hot_r",      # reversed: less sun = better (shade = good)

    # Scoring (hot climate — higher sun/UTCI is worse)
    "score_config": {
        "wind_label":   "Wind stagnation",
        "wind_metric":  "frac_lt1ms",
        "wind_bad":     "<1 m/s = stifling, no evaporative cooling",
        "wind_worst":   0.75, "wind_best": 0.05,
        "wind_weight":  0.20,

        "solar_label":  "Solar overexposure",
        "solar_metric": "frac_gt5h",
        "solar_bad":    ">5 h direct sun/day in July = dangerously exposed",
        "solar_worst":  0.85, "solar_best": 0.10,
        "solar_weight": 0.35,

        "utci_label":   "Heat stress",
        "utci_metric":  "frac_utci_bad",
        "utci_bad":     "UTCI > 38 C (strong heat stress, July)",
        "utci_worst":   0.95, "utci_best": 0.10,
        "utci_weight":  0.45,
        "utci_thresh":  38,
        "utci_bad_dir": "above",
    },

    # Scenarios
    "scenario_A": {
        "label":       "Date palm shade grid (513 trees, courtyard)",
        "tree_fn":     _mecca_shade_trees,
        "tree_props":  {"height": 12, "crown_radius": 4, "genus": "Phoenix"},
        "ground_key":  None,
    },
    "scenario_B": {
        "label":       "Asphalt -> pale concrete (high-albedo paving)",
        "tree_fn":     None,
        "ground_key":  "concrete",
        "ground_fc":   _inner_polygon(_MKK_LAT, _MKK_LON, size_m=600),
    },
    "scenario_C_label": "513 date palms + pale concrete (combined)",
}
