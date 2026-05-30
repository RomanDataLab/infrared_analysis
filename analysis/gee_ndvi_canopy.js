// ============================================================
//  Tree-canopy extraction from NDVI (Sentinel-2)
//  Cities: Almaty, Riyadh, Astana, Mecca
//
//  Bounding boxes are the EXACT 1 500 m context polygons used in
//  baseline.py (same area as the Infrared SDK building/veg fetch).
//  Computed from sites.py _polygon_context(lat_c, lon_c, 1500).
//
//  Paste into: https://code.earthengine.google.com
//  ▶ Run → check Task tab → Run each export task
//  Download the four GeoJSON files from Google Drive, then:
//    python postprocess_ndvi.py --site almaty --geojson Almaty_canopy_polygons.geojson
//    python postprocess_ndvi.py --site riyadh --geojson Riyadh_canopy_polygons.geojson
//    python postprocess_ndvi.py --site astana --geojson Astana_canopy_polygons.geojson
//    python postprocess_ndvi.py --site mecca  --geojson Mecca_canopy_polygons.geojson
// ============================================================

// ---- 1. Site rectangles  [west, south, east, north] ---------
//
//  Almaty  centre 43.2450 N, 76.9480 E   → context 1500 m
//  Riyadh  centre 24.6922 N, 46.7088 E   → context 1500 m
//  Astana  centre 51.1605 N, 71.4058 E   → context 1500 m
//  Mecca   centre 21.4265 N, 39.8135 E   → context 1500 m
//
var sites = {
  Almaty: {
    aoi:          ee.Geometry.Rectangle([76.9387, 43.2383, 76.9573, 43.2517]),
    genus:        'Betula',   // birch — dominant street tree in Almaty
    tree_height:  8,
    crown_radius: 3
  },
  Riyadh: {
    aoi:          ee.Geometry.Rectangle([46.7014, 24.6855, 46.7163, 24.6990]),
    genus:        'Phoenix',  // date palm — dominant urban tree in Riyadh
    tree_height:  10,
    crown_radius: 4
  },
  Astana: {
    aoi:          ee.Geometry.Rectangle([71.395026, 51.153784, 71.416512, 51.167258]),
    genus:        'Ulmus',    // elm — common in Astana boulevard plantings
    tree_height:  8,
    crown_radius: 3
  },
  Mecca: {
    aoi:          ee.Geometry.Rectangle([39.8063, 21.4198, 39.8208, 21.4333]),
    genus:        'Phoenix',  // date palm
    tree_height:  10,
    crown_radius: 4
  }
};

// ---- 2. Parameters -------------------------------------------
var YEAR_START     = '2024-01-01';
var YEAR_END       = '2025-01-01';
// NDVI threshold: 0.35 separates irrigated woody vegetation from
// bare desert (0.05–0.15) and sparse dry shrubs (0.15–0.30).
// Height filter ensures we capture trees, not grass/lawn.
var NDVI_THRESH    = 0.35;
var MIN_HEIGHT_M   = 3.5;    // metres — Meta canopy height model cutoff
var EXPORT_SCALE_M = 10;     // Sentinel-2 native resolution

// ---- 3. Data sources -----------------------------------------
var s2  = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED');
var csp = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');
// Meta (Facebook) global canopy height model, ~1 m vertical resolution
var chm = ee.ImageCollection(
  'projects/sat-io/open-datasets/facebook/meta-canopy-height'
).mosaic();

// Keep only clear pixels (Cloud Score+ threshold ≥ 0.60)
function maskClouds(img) {
  return img.updateMask(img.select('cs').gte(0.60));
}

// ---- 4. Per-city processing ----------------------------------
function processCity(name, info) {
  var aoi = info.aoi;

  // Build cloud-masked image collection and compute per-image NDVI
  var coll = s2
    .filterBounds(aoi)
    .filterDate(YEAR_START, YEAR_END)
    .linkCollection(csp, ['cs'])
    .map(maskClouds)
    .map(function(img) {
      return img.addBands(
        img.normalizedDifference(['B8', 'B4']).rename('NDVI')
      );
    });

  // Max-NDVI composite: captures peak leaf-out for deciduous (Almaty/Astana)
  // and peak irrigation flush for palms (Riyadh/Mecca) in a single pass.
  var ndvi = coll.qualityMosaic('NDVI').select('NDVI').clip(aoi);

  // Canopy mask: green (NDVI ≥ threshold) AND tall (CHM ≥ 3.5 m)
  var canopy = ndvi.gte(NDVI_THRESH)
                   .and(chm.gte(MIN_HEIGHT_M))
                   .selfMask()
                   .rename('canopy');

  // ---- Report canopy area ----
  var areaHa = canopy
    .multiply(ee.Image.pixelArea())
    .reduceRegion({
      reducer:   ee.Reducer.sum(),
      geometry:  aoi,
      scale:     EXPORT_SCALE_M,
      maxPixels: 1e9
    })
    .getNumber('canopy')
    .divide(1e4);
  print(name + ' — canopy area (ha):', areaHa);

  // ---- Visualise (toggle layers in Map panel) ----
  Map.addLayer(
    ndvi,
    { min: 0, max: 0.8, palette: ['white', 'khaki', 'darkgreen'] },
    name + ' NDVI', false
  );
  Map.addLayer(canopy, { palette: ['#1d9e75'] }, name + ' canopy');
  Map.addLayer(
    aoi,
    { color: 'yellow', fillColor: '00000000' },
    name + ' context bbox'
  );

  // ---- Vectorise canopy mask → polygons ----
  var vectors = canopy.reduceToVectors({
    geometry:     aoi,
    scale:        EXPORT_SCALE_M,
    geometryType: 'polygon',
    maxPixels:    1e9,
    bestEffort:   true
  });

  // Annotate each polygon with tree-species metadata so
  // postprocess_ndvi.py can assign the right genus/height/crown_radius.
  vectors = vectors.map(function(f) {
    return f.set({
      genus:        info.genus,
      tree_height:  info.tree_height,
      crown_radius: info.crown_radius,
      site_name:    name
    });
  });

  // ---- Export vector polygons as GeoJSON (postprocess_ndvi.py reads this) ----
  Export.table.toDrive({
    collection:  vectors,
    description: name + '_canopy_polygons',
    folder:      'RenovationMap_NDVI',
    fileFormat:  'GeoJSON'
  });
}

// ---- 5. Run all four -----------------------------------------
Object.keys(sites).forEach(function(name) {
  processCity(name, sites[name]);
});

// Centre map on Astana (steppe city with sparse OSM tree data)
Map.centerObject(sites.Astana.aoi, 13);
