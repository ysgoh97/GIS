// Define variables.
var start = '2023-06-12';
var end = '2024-06-12';
var outfile = 'sentinel2_202406_jh';
var out = 'asset'; // asset, gdrive, both
var cloud = 's2cloudless'; // QA60, s2cloudless
var max_cloud_perc = 50;
var objects = ee.List(['mangrove']) // mangrove
var aoi = ee.Geometry.Polygon(
        [[[103.40076631968488, 1.7318153713127193],
          [103.40076631968488, 1.2444629609037825],
          [104.330484337263, 1.2444629609037825],
          [104.330484337263, 1.7318153713127193],
          [103.40076631968488, 1.7318153713127193]]], null, false);


// Load Sentinel-2 surface reflectance data.
var dataset = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                .filterDate(start, end)
                .filterBounds(aoi)
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_perc));
print(dataset);


// QA60 cloud masking.
function qa60(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10; // Bits 10 are clouds
  var cirrusBitMask = 1 << 11; // Bits 11 are cirrus
  
  // Both flags should be set to zero, indicating clear conditions.
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask).divide(10000);
}
if (cloud == 'QA60') {
  dataset = dataset.map(qa60);
}


// s2cloudless cloud masking.
// See a similar script for the Python API here:
// https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless
  
// Join the cloud probability dataset to surface reflectance.
// Join the L1C data to get the bands needed for CDI.
function indexJoin(collectionA, collectionB, propertyName) {
  var joined = ee.ImageCollection(ee.Join.saveFirst(propertyName).apply({
    primary: collectionA,
    secondary: collectionB,
    condition: ee.Filter.equals({
      leftField: 'system:index',
      rightField: 'system:index'})
  }));
  return joined.map(function(image) {
    return image.addBands(ee.Image(image.get(propertyName)));
  });
}

// Mask clouds and shadows.
function maskImage(image) {
  var cdi = ee.Algorithms.Sentinel2.CDI(image);
  var s2c = image.select('probability');
  var cirrus = image.select('B10').divide(10000);
  
  // Assume low-to-mid atmospheric clouds to be pixels where probability
  // is greater than 65%, and CDI is less than -0.5. For higher atmosphere
  // cirrus clouds, assume the cirrus band is greater than 0.01.
  // The final cloud mask is one or both of these conditions.
  var isCloud = s2c.gt(65).and(cdi.lt(-0.5)).or(cirrus.gt(0.01));

  // Reproject is required to perform spatial operations at 20m scale.
  // 20m scale is for speed, and assumes clouds don't require 10m precision.
  isCloud = isCloud.focal_min(3).focal_max(16);
  isCloud = isCloud.reproject({crs: cdi.projection(), scale: 20});

  // Project shadows from clouds we found in the last step. This assumes we're working in
  // a UTM projection.
  var shadowAzimuth = ee.Number(90)
      .subtract(ee.Number(image.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

  // With the following reproject, the shadows are projected 5km.
  isCloud = isCloud.directionalDistanceTransform(shadowAzimuth, 50);
  isCloud = isCloud.reproject({crs: cdi.projection(), scale: 100});
  isCloud = isCloud.select('distance').mask();
  return image.select('.*').updateMask(isCloud.not()).divide(10000);
}
if (cloud == 's2cloudless') {
  var s2 = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
    .filterBounds(aoi)
    .filterDate(start, end);
  var s2c = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
    .filterBounds(aoi)
    .filterDate(start, end);
  var withCloudProbability = indexJoin(dataset, s2c, 'cloud_probability');
  var withS2L1C = indexJoin(withCloudProbability, s2, 'l1c');
  var masked = ee.ImageCollection(withS2L1C.map(maskImage));
  dataset = masked.select(dataset.first().bandNames());
}


// Create mosaic (median composite).
var image = dataset.median().select('B.*');


/* Spectral indices

Mangroves:
  >> https://doi.org/10.1038/s41598-024-57563-4
  >> https://doi.org/10.1016/j.mex.2024.102778

*/
if (objects.contains('mangrove')) {
  var ndvi = image.expression(
    '(NIR-RED)/(NIR+RED)', {
      'NIR': image.select('B8'),
      'RED': image.select('B4')
  }).rename("NDVI");
  image = image.addBands(ndvi);
  var evi = image.expression(
    '2.5*(NIR-RED)/(NIR+6*RED-7.5*BLUE+1)', {
      'NIR': image.select('B8'),
      'RED': image.select('B4'),
      'BLUE': image.select('B2'),
  }).rename("EVI");
  image = image.addBands(evi);
  var gndvi = image.expression(
    '(NIR-GREEN)/(NIR+GREEN)', {
      'NIR': image.select('B8'),
      'GREEN': image.select('B3')
  }).rename("GNDVI");
  image = image.addBands(gndvi);
  var rendvi = image.expression(
    '(RE2-RE1)/(RE2+RE1)', {
      'RE2': image.select('B6'),
      'RE1': image.select('B5')
  }).rename("ReNDVI");
  image = image.addBands(rendvi);
  var arvi2 = image.expression(
    '-0.18+1.17*((NIR-RED)/(NIR+RED))', {
      'NIR': image.select('B8'),
      'RED': image.select('B4')
  }).rename("ARVI2");
  image = image.addBands(arvi2);
  var savi = image.expression(
    '(NIR-RED)/(NIR+RED+L)', {
      'NIR': image.select('B8'),
      'RED': image.select('B4'),
      'L': 0.5 
      // L = [0:1]; 0.5 (medium canopy); 0.75 (dense canopy)
  }).rename("SAVI");
  image = image.addBands(savi);
  var ndwi = image.expression(
    '(NIR-SWIR)/(NIR+SWIR)', {
      'NIR': image.select('B8'),
      'SWIR': image.select('B11')
  }).rename("NDWI");
  image = image.addBands(ndwi);
  var mi = image.expression(
    '((NIR-SWIR)/(NIR*SWIR))*10000', {
      'NIR': image.select('B8'),
      'SWIR': image.select('B11')
  }).rename("MI");
  image = image.addBands(mi);
  var cmri = image.expression(
    'NDVI-NDWI', {
      'NDVI': image.select('NDVI'),
      'NDWI': image.select('NDWI')
  }).rename("CMRI");
  image = image.addBands(cmri);
  var mvi = image.expression(
    '(NIR-GREEN)/(SWIR-GREEN)', {
      'NIR': image.select('B8'),
      'GREEN': image.select('B3'),
      'SWIR': image.select('B11')
  }).rename("MVI");
  image = image.addBands(mvi);
  var ammi = image.expression(
    '(NIR-RED)/(RED+SWIR)*(NIR-SWIR)/(SWIR-0.65*RED)', {
      'NIR': image.select('B8'),
      'RED': image.select('B4'),
      'SWIR': image.select('B11')
  }).rename("AMMI");
  image = image.addBands(ammi);
  var emi = image.expression(
    '(NIR-SWIR)/(GREEN+NIR)', {
      'NIR': image.select('B8'),
      'GREEN': image.select('B3'),
      'SWIR': image.select('B11')
  }).rename("EMI");
  image = image.addBands(emi);
}
image = image.toFloat().clip(aoi)
print(image)


// Visualize.
var rgbVis = {
  min: 0.0,
  max: 1.0,
  gamma: 1.2,
  bands: ['B4', 'B3', 'B2'],
};
Map.centerObject(aoi, 11);
Map.addLayer(image, rgbVis, 'RGB');


// Export the image
if (out == 'gdrive' || out == 'both') {
  Export.image.toDrive({
    image: image,
    description: outfile,
    folder: 'Downloads',
    crs: image.crs,
    scale: 10,
    region: aoi
  });
}
if (out == 'asset' || out =='both') {
  Export.image.toAsset({
    image: image,
    description: outfile,
    crs: image.crs,
    scale: 10,
    region: aoi
  });
}
