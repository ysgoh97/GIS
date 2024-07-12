# DJI P4 Multispectral Image Processing
Photogrammetry is commonly used to create orthomosaics from drone images. However, photogrametry may not be able to align water areas as the constantly moving surfaces and sunglint effects may result result in a lack of tie points. MicaSense has resolved this by creating python scripts that can individually process MicaSense images. 

This repository is an attempt to adapt the MicaSense python scripts for DJI P4 Multispectral images.


## Code Structure
```
   .
   ├── helper                       <--- helper scripts adapted from micasense
   │    └── metadata.py             
   ├── 1_DjiP4M_Correction.ipynb    <--- correct for phase difference, vignette effect, distortion, sunlight
   ├── 2_DjiP4M_Stacking.ipynb      <--- align and stack corrected bands
   └── conda_env.yml                <--- conda environment requirements
``` 


## Disclaimer
* This repository is incomplete and still under testing. As this is my first attempt at drone image processing, and the [P4 Multispectral Image Processing Guide](https://dl.djicdn.com/downloads/p4-multispectral/20200717/P4_Multispectral_Image_Processing_Guide_EN.pdf) referenced is not clear, any feedback would be greatly appreciated.

    | Outstanding Issues    | Possible Solutions (To Test)  |
    |---    |---    |
    | As DJI P4M does not provide the conversion parameter, p_nir, to convert image signal values to reflectance values, reflectance is currently estimated by normalizing sunlight sensor adjusted values to [0,1] | If better image processing methods are available (e.g. land areas produced using Agisoft Metashape), the normalized values can be adjusted to fit the better images. However, datasets obtained from different flight missions will remain incomparable without radiometric calibration using calibrated reflectance panels.  |
    | findTransformECC fails to converge for some image.    | Refer to how MicaSense scripts handle this.   |


* The position of the processed images will not be able to achieve the accuracy of orthomaps generated using photogrammetry.
* This repository does not include the script to georeference the processed images as a paid software (ArcGIS), was used for georeferencing.


## References
* [P4 Multispectral Image Processing Guide](https://dl.djicdn.com/downloads/p4-multispectral/20200717/P4_Multispectral_Image_Processing_Guide_EN.pdf) 
* [MicaSense RedEdge and Altum Image Processing Tutorials](https://github.com/micasense/imageprocessing)