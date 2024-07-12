/* References: 
Mangrove Classification: https://doi.org/10.1038/s41598-024-57563-4
GEE LULC Classification: https://doi.org/10.3390/rs12223776
GEE LULC Code: https://code.earthengine.google.com/?accept_repo=users/mvizzari/Tassi_Vizzari_RS2020
*/



// 1) ----- Define variables -----
var train_image = ee.Image("projects/gee-ysgoh/assets/sentinel2_2022_jh");
var test_image = ee.Image("projects/gee-ysgoh/assets/sentinel2_2022_jh");
var classify_image = ee.Image("projects/gee-ysgoh/assets/sentinel2_202406_jh");
var label = ee.FeatureCollection("projects/gee-ysgoh/assets/Labels/SGMY_Mangrove_2024");
var outfile = 'sentinel2_202406_jh_mangrove';
var out = 'gdrive'; // asset, gdrive, both

var split = 0.3; // train-test split [0:1]
var buffer_m = 10; // buffer to get more information
var s2vis = {
  min: 0.0,
  max: 1.0,
  bands: ["B4", "B3", "B2"],
  };
var lulc_class = ['Non-mangrove', 'Mangrove'];
var lulc_palette = [ 
  'FFFF00', //(0)  Non-mangrove
  '00FF00' //(1) Mangrove
];  

// Classification parameters.
var classify_type = "PB"; // (OB) object-based, (PB) pixel-based

// GLCM parameters.
var glcm_neighbor = 3;
var glcm_bands= ["gray_corr","gray_ent","gray_idm","gray_savg"];

// PCA parameters.
var pca_bands = ["pc1"];

// SNIC parameters.
var snic_seedspace = 10; // superpixel seed location spacing, in pixels: (5 - 10 - 15 - 20)
var snic_compact = 1; // 0 disables spatial distance weighting. Larger values creates more compact (square) clusters.
var snic_connect = 8; // 4 directions or 8 directions
var snic_neighbor = 256; // tile neighborhood size (to avoid tile boundary artifacts)

// RF parameters.
var rf_trees = 50; // number of decision trees



// 2) ----- Data -----
// Creation of the feature collection using pixels labelled with "LULC".
label = label.randomColumn();
var train_fc = label.filter(ee.Filter.greaterThan('random', split));
var test_fc = label.filter(ee.Filter.lessThan('random', split));

// Plot.
var setPointProperties = function(f){
  var label_class = f.get("LULC");
  var mapDisplayColors = ee.List(lulc_palette); // class 0 should be blue, class 1 should be red
  return f.set({style: {color: mapDisplayColors.get(label_class)}});
};
Map.addLayer(train_image, s2vis, 'S2 RGB (Train)', false);
Map.addLayer(train_fc.map(setPointProperties).style({styleProperty: "style"}), {}, 'Train', false);
Map.addLayer(test_image, s2vis, 'S2 RGB (Test)');
Map.addLayer(test_fc.map(setPointProperties).style({styleProperty: "style"}), {}, 'Test');
//Map.addLayer(classify_image, s2vis, 'S2 RGB (Classify)', false);

// Improve the information using a buffer.
if (buffer_m !== 0) {
  var buffer = function(feature) {
    return feature.buffer(buffer_m);
  };
  train_fc = train_fc.map(buffer);
}



// 3) ----- Gray Level Co-occurrence Matrix -----
// Create and rescale a grayscale image for GLCM.
var glcm_fn = function(dataset) {
  var gray = dataset.expression(
        '(0.3 * NIR) + (0.59 * R) + (0.11 * G)', {
        'NIR': dataset.select('B8'),
        'R': dataset.select('B4'),
        'G': dataset.select('B3')
  }).rename('gray');
  
  // The glcmTexture size (in pixel) can be adjusted considering the spatial resolution and the object textural characteristics.
  var glcm = gray.unitScale(0, 0.30).multiply(100).toInt().glcmTexture({size: glcm_neighbor});
  
  // Before the PCA the glcm bands are scaled.
  var image = glcm.select(glcm_bands);
  
  // Calculate the min and max value of an image.
  var minMax = image.reduceRegion({
    reducer: ee.Reducer.minMax(),
    scale: 10,
    bestEffort: true
  }); 
  glcm = ee.ImageCollection.fromImages(
    image.bandNames().map(function(name){
      name = ee.String(name);
      var band = image.select(name);
        return band.unitScale(ee.Number(minMax.get(name.cat('_min'))), ee.Number(minMax.get(name.cat('_max'))));
    }
  )).toBands().rename(image.bandNames());
  return glcm;
};
var train_glcm = glcm_fn(train_image);
var test_glcm = glcm_fn(test_image);
var classify_glcm = glcm_fn(classify_image);


// 4) ----- Principal Component Analysis -----
// Adapted from: https://developers.google.com/earth-engine/guides/arrays_eigen_analysis)

var pca_fn = function(dataset) {
  // Mean center the data to enable a faster covariance reducer and an SD stretch of the principal components.
  var aoi = dataset.geometry();
  var scale = dataset.projection().nominalScale();
  var bandNames = dataset.bandNames();
  var meanDict = dataset.reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: aoi, 
      scale: scale,
      bestEffort: true
  });
  var means = ee.Image.constant(meanDict.values(bandNames));
  var centered = dataset.subtract(means);
  
  // This helper function returns a list of new band names.
  var getNewBandNames = function(prefix) {
    var seq = ee.List.sequence(1, bandNames.length());
    return seq.map(function(b) {
      return ee.String(prefix).cat(ee.Number(b).int());
    });
  };

  var getPrincipalComponents = function(centered, scale, region) {
    // Collapse the bands of the image into a 1D array per pixel.
    var arrays = centered.toArray();
    
    // Compute the covariance of the bands within the region.
    var covar = arrays.reduceRegion({
      reducer: ee.Reducer.centeredCovariance(),
      geometry: region,
      scale: scale, 
      bestEffort: true
    });
    
    // Get the 'array' covariance result and cast to an array.
    // This represents the band-to-band covariance within the region.
    var covarArray = ee.Array(covar.get('array'));
    
    // Perform an eigen analysis and slice apart the values and vectors.
    var eigens = covarArray.eigen();
    
    // This is a P-length vector of Eigenvalues.
    var eigenValues = eigens.slice(1, 0, 1);
    // This is a PxP matrix with eigenvectors in rows.
    var eigenVectors = eigens.slice(1, 1);
      
    // Convert the array image to 2D arrays for matrix computations.
    var arrayImage = arrays.toArray(1);
      
    // Left multiply the image array by the matrix of eigenvectors.
    var principalComponents = ee.Image(eigenVectors).matrixMultiply(arrayImage);
      
    // Turn the square roots of the Eigenvalues into a P-band image.
    var sdImage = ee.Image(eigenValues.sqrt())
      .arrayProject([0]).arrayFlatten([getNewBandNames('sd')]);
    
    // Turn the PCs into a P-band image, normalized by SD.
    return principalComponents
      // Throw out an an unneeded dimension, [[]] -> [].
      .arrayProject([0])
      // Make the one band array image a multi-band image, [] -> image.
      .arrayFlatten([getNewBandNames('pc')])
      // Normalize the PCs by their SDs.
      .divide(sdImage);
  };
  
  // Get the PCs at the specified scale and in the specified region
  var pcImage = getPrincipalComponents(centered, scale, aoi);
  return pcImage.select(pca_bands);
};
var train_pca = pca_fn(train_glcm);
var test_pca = pca_fn(test_glcm);
var classify_pca = pca_fn(classify_glcm);



// 5) ----- Clustering (if applicable) -----

// Object-based approach.
if (classify_type == "OB") {
  
  var ob_fn = function(dataset, pca) {
    
    // Segmentation using SNIC.
    var seeds = ee.Algorithms.Image.Segmentation.seedGrid(snic_seedspace);
    var snic = ee.Algorithms.Image.Segmentation.SNIC({
      image: dataset, 
      compactness: snic_compact,  
      connectivity: snic_connect, 
      neighborhoodSize: snic_neighbor, 
      seeds: seeds
    });
    
    // Calculate the mean for each segment with respect to the pixels in that cluster.
    var clusters_snic = snic.select("clusters");
    clusters_snic = clusters_snic.reproject ({crs: clusters_snic.projection (), scale: 10});
    //Map.addLayer(clusters_snic.randomVisualizer(), {}, 'Clusters', false)
    
    // Add PCA data.
    var new_feature = clusters_snic.addBands(pca);
    var new_feature_mean = new_feature.reduceConnectedComponents({
      reducer: ee.Reducer.mean(),
      labelBand: 'clusters'
    });
  
    // Add clusters
    dataset = new_feature_mean.addBands(snic);
    return dataset;
  };
  var train_image = ob_fn(train_image, train_pca);
  var test_image = ob_fn(test_image, test_pca);
  var classify_image = ob_fn(classify_image, classify_pca);
  
  // Define the training bands removing just the "clusters" bands.
  var bands = train_image.bandNames().remove("clusters");
  var training = train_image.select(bands).sampleRegions({
  collection: train_fc,
  properties: ['LULC'],
  scale: 10
  });
}

// Pixel-based approach.
else if (classify_type == "PB") {
  
  // Add PCA data.
  train_image = train_image.addBands(train_pca);
  test_image = test_image.addBands(test_pca);
  classify_image = classify_image.addBands(classify_pca);
  
  // Get the predictors into the table and create a training dataset based on "LULC" property
  var bands = train_image.bandNames();
  var training = train_image.select(bands).sampleRegions({
    collection: train_fc,
    properties: ['LULC'],
    scale: 10
  });
}

else {
  print("Please set a valid classification type (OB / PB).");
}



// 6) ----- Training -----
// Random forest.
var classifier =  ee.Classifier.smileRandomForest(rf_trees).train({
  features: training,
  classProperty: 'LULC',
  inputProperties: bands
}); 

// Clip and filter the result.
var classified = train_image.select(bands).classify(classifier);

// Accuracy metrics.
print('Confusion matrix (train): ', classifier.confusionMatrix());
print('Accuracy (train): ', classifier.confusionMatrix().accuracy());



// 7) ----- Validation -----
var classifierTest = test_image.select(bands).sampleRegions({
  collection: test_fc,
  properties: ['LULC'],
  scale: 10
});
var classified_test = classifierTest.classify(classifier);
var testAccuracy = classified_test.errorMatrix('LULC', 'classification');
print('Confusion matrix (test): ', testAccuracy);
print('Accuracy (test): ', testAccuracy.accuracy());



// 8) ----- Classification -----
var classified_final = classify_image.select(bands).classify(classifier);



// 9) ---- Visualize -----
// Visualize raw data.
var lulcviz = {
  min: 0, 
  max: lulc_class.length, 
  palette: lulc_palette
  
};
Map.centerObject(classified_final.geometry(), 11);
//Map.addLayer(classified_final, lulcviz, 'LULC');

// Set position of panel.
var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px'
  }
});
 
// Create legend title.
var legendTitle = ui.Label({
  value: 'Legend',
  style: {
    fontWeight: 'bold',
    fontSize: '18px',
    margin: '0 0 4px 0',
    padding: '0'
    }
});

// Add the title to the panel.
legend.add(legendTitle);
 
// Creates and styles 1 row of the legend.
var makeRow = function(color, name) {
 
      // Create the label that is actually the colored box.
      var colorBox = ui.Label({
        style: {
          backgroundColor: '#' + color,
          
          // Use padding to give the box height and width.
          padding: '8px',
          margin: '0 0 4px 0'
        }
      });
 
      // Create the label filled with the description text.
      var description = ui.Label({
        value: name,
        style: {margin: '0 0 4px 6px'}
      });
 
      // Return the panel.
      return ui.Panel({
        widgets: [colorBox, description],
        layout: ui.Panel.Layout.Flow('horizontal')
      });
};

// Add color and and names.
for (var i = 0; i < lulc_class.length; i++) {
  legend.add(makeRow(lulc_palette[i], lulc_class[i]));
  }  
  
// Add legend to map (alternatively you can also print the legend to the console)
Map.add(legend);


// 10) ---- Export LULC map result.
if (out == 'gdrive' || out == 'both') {
  Export.image.toDrive({
    image: classified_final,
    description: outfile,
    folder: 'Downloads',
    crs: classified_final.crs,
    scale: 10
  });
}
if (out == 'asset' || out =='both') {
  Export.image.toAsset({
    image: classified_final,
    description: outfile,
    crs: classified_final.crs,
    scale: 10
  });
}
