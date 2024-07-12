// Define variables.
var start = '2023-01-01';
var end = '2023-12-12';
var outfile = 'landsat_2023';
var out = 'gdrive'; // asset, gdrive, both
var aoi = ee.Geometry.Polygon(
  [[[103.34583467905988, 1.7647590129350037],
    [103.34583467905988, 1.2499548235708902],
    [104.13959688609113, 1.2499548235708902],
    [104.13959688609113, 1.7647590129350037]]], null, false);


//Function to mask clouds based on the pixel_qa band.
function maskL8sr(image) {
  // Bits 3 and 5 are cloud shadow and cloud, respectively.
  var cloudShadowBitMask = (1 << 3);
  var cloudsBitMask = (1 << 5);
  // Get the pixel QA band.
  var qa = image.select('QA_PIXEL');
  // Both flags should be set to zero, indicating clear conditions.
  var mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0)
                 .and(qa.bitwiseAnd(cloudsBitMask).eq(0));
  return image.updateMask(mask);
}


// Applies scaling factors.
function applyScaleFactors(image) {
  var opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2);
  var thermalBand = image.select('ST_B6').multiply(0.00341802).add(149.0);
  return image.addBands(opticalBands, null, true)
              .addBands(thermalBand, null, true);
}


// Load Landsat 5 surface reflectance.
var dataset = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .filterDate(start, end)
    .filterBounds(aoi)
    .map(maskL8sr)
    .map(applyScaleFactors);
print(dataset)


// Create mosaic (median composite).
var mosaic = dataset.median().select('SR_B.*')


// Visualize.
var rgbVis = {
  bands: ['SR_B3', 'SR_B2', 'SR_B1'],
  min: 0.0,
  max: 0.3,
};
Map.centerObject(aoi, 11);
Map.addLayer(mosaic, rgbVis, 'RGB');


if (out == 'asset' || out == 'both') {
  Export.image.toAsset({
    image: image,
    description: outfile,
    crs: image.crs,
    scale: 30,
    region: aoi
  });
}