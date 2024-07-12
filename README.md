# GIS
 
## Introduction
This repository contains scripts that are useful for GIS applications.

## Code & File Structure
```
    .
    ├── Arcpy
    │   ├── ArcMap_Python
    │   │   ├── Input
    │   │   ├── Output
    │   │   ├── Template
    │   │   │   ├── LYR
    │   │   │   └── MXD
    │   │   └── arcmap_basic_plot.py
    │   ├── ArcPro_Python
    │   │   ├── Input
    │   │   ├── Output
    │   │   ├── Template
    │   │   │   ├── APRX
    │   │   │   └── LYRX
    │   │   └── arcpro_basic_plot.py
    │   └── ArcMap_Toolbox
    │       └── water_depth_correction.py
    ├── Satellite
    │   ├── Python_API 
    │   │   ├── Sentinel_OData.py
    │   │   └── Sentinel3TSM_EUMDAC.py
    │   └── GEE
    │       ├── Download_Landsat5SR.js
    │       ├── Download_Sentinel2SR.js
    │       └── LULC_RandomForest.js
    └── UAV
        └── DJI_P4M
```

## Arcpy
### ArcMap_Python
This folder contains python script for ArcMap 10.7.1 & Python 2.7

#### basic_plot.py
* Plot raster and shapefile on template mxd file
* Update symbology using lyr file
* Set layer transparency
* Turn on and format labels
* Edit texts in template mxd file
* Zoom in to each feature in shapefile

### ArcPro_Python
This folder contains python script for ArcGIS Pro 3.1 & Python 3.9

#### basic_plot.py
* Zoom to layer
* Edit values for stretched raster color bar
* Edit texts in template mxd file

### ArcMap_Toolbox
This folder contains script to be run in ArcMap 10.7.1 toolbox.

#### water_depth_correction.py
Implementation of the following article: Edwards, A. J., & MUMBY, P. (1999). Compensating for variable water depth to improve mapping of underwater habitats: why it is necessary. *Applications of Satellite and Airborne Image Data to Coastal Management*, 121-136. [[URL](https://www.ncl.ac.uk/tcmweb/bilko/module7/lesson5.pdf)]

## Satellite
### Python_API
This folder contains python script to download satellite images using various API.

#### Sentinel_OData.py
Download Sentinel satellite images from Copernicus Data Space Ecosystem using the [OData API](https://documentation.dataspace.copernicus.eu/APIs/OData.html).

#### Sentinel3TSM_EUMDAC.py
Download Sentinel 3 TSM (total suspended matter) images from EUMETSAT using the [EUMDAC API](https://user.eumetsat.int/resources/user-guides/eumetsat-data-access-client-eumdac-guide#ID-Python-library).

### GEE
This folder contains script to process satellite images in [Google Earth Engine (GEE)](https://code.earthengine.google.com/).

#### Download_Landsat5SR.js
* Get Landsat 5 surface reflectance images from GEE database
* Remove clouds
* Create median composites
* Export to GEE asset / Google Drive

#### Download_Sentinel2SR.js
* Get Sentinel 2 surface reflectance images from GEE database
* Remove clouds (QA60 / s2cloudless)
* Calculate spectral indices (for mangrove monitoring)
* Create median composites
* Export to GEE asset / Google Drive

#### LULC_RandomForest.js
Land use land cover classification
* Current parameters are optimized for mangrove monitoring
* Use Gray Level Co-occurrence Matrix & Principal Component Analysis to extract textural features
* Use Simple Non-Iterative Clustering for clustering
* Use Random Forest for classification

Adapted from: 
* Tassi, A., & Vizzari, M. (2020). Object-oriented lulc classification in google earth engine combining snic, glcm, and machine learning algorithms. *Remote Sensing, 12*(22), 3776. [[Publication](https://www.mdpi.com/2072-4292/12/22/3776) | [Code](https://code.earthengine.google.com/?accept_repo=users/mvizzari/Tassi_Vizzari_RS2020)]
* Sunkur, R., Kantamaneni, K., Bokhoree, C., Rathnayake, U., & Fernando, M. (2024). Mangrove mapping and monitoring using remote sensing techniques towards climate change resilience. *Scientific Reports, 14*(1), 6949. [[Publication](https://www.nature.com/articles/s41598-024-57563-4)]

## UAV
### DJI_P4M
Photogrammetry is commonly used to create orthomosaics from drone images. However, photogrametry may not be able to align water areas as the constantly moving surfaces and sunglint effects may result result in a lack of tie points. MicaSense has resolved this by creating python scripts that can individually process MicaSense images. 

This repository is an attempt to adapt the MicaSense python scripts for DJI P4 Multispectral images.

```
   .
    └── UAV
        └── DJI_P4M
            ├── helper                       
            │    └── metadata.py             
            ├── 1_DjiP4M_Correction.ipynb    <--- correct for phase difference, vignette, distortion, sunlight
            ├── 2_DjiP4M_Stacking.ipynb      <--- align and stack corrected bands
            └── conda_env.yml                <--- conda environment requirements
``` 

WARNING
* This repository is incomplete and still under testing. As this is my first attempt at drone image processing, and the [P4 Multispectral Image Processing Guide](https://dl.djicdn.com/downloads/p4-multispectral/20200717/P4_Multispectral_Image_Processing_Guide_EN.pdf) referenced is not clear, any feedback would be greatly appreciated.
* The position of the processed images will not be able to achieve the accuracy of orthomaps generated using photogrammetry.
* This repository does not include the script to georeference the processed images as a paid software (ArcGIS), was used for georeferencing.

| Outstanding Issues    | Possible Solutions (To Test)  |
|---    |---    |
| As DJI P4M does not provide the conversion parameter, p_nir, to convert image signal values to reflectance values, reflectance is currently estimated by normalizing sunlight sensor adjusted values to [0,1] | If better image processing methods are available (e.g. land areas produced using Agisoft Metashape), the normalized values can be adjusted to fit the better images. However, datasets obtained from different flight missions will remain incomparable without radiometric calibration using calibrated reflectance panels.  |
| findTransformECC fails to converge for some image.    | Refer to how MicaSense scripts handle this.   |

References:
* [P4 Multispectral Image Processing Guide](https://dl.djicdn.com/downloads/p4-multispectral/20200717/P4_Multispectral_Image_Processing_Guide_EN.pdf) 
* [MicaSense RedEdge and Altum Image Processing Tutorials](https://github.com/micasense/imageprocessing)
