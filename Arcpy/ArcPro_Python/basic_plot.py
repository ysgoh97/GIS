"""
Arcpy script to plot raster

Author: Yun Si
Last modified: 20240613
Tested on: ArcGIS Pro 3.1 & Python 3.9
"""

print("Initializing...")
import os, shutil, sys, traceback, time
import arcpy


########## ---------- Settings ---------- ##########
# Environmental variables
cwd = os.getcwd()
overwrite = True

# Input data
in_tif = os.path.join(cwd, "Input", "raster.tif")

# Input template map
in_aprx = os.path.join(cwd, "Template", "APRX", "map.aprx")

# Input template symbology
sym_tif = os.path.join(cwd, "Template", "LYRX", "raster.lyrx")

# Output directory
out_aprx = os.path.join(cwd, "Output", "APRX")
out_png = os.path.join(cwd, "Output", "PNG")
out_filename = "out"


########## ---------- SYS CHECK ---------- ##########
if not os.path.exists(out_aprx):
    os.mkdir(out_aprx)
elif overwrite and os.path.exists(out_aprx):
    os.remove(os.path.join(out_aprx, out_filename + ".aprx"))

if not os.path.exists(out_png):
    os.mkdir(out_png)
if overwrite and os.path.exists(out_png):
    os.remove(os.path.join(out_png, out_filename + ".png"))

temp_name = "Working.gdb"
arcpy.env.overwriteOutput = overwrite
if os.path.exists(os.path.join(out_aprx, temp_name)):
    shutil.rmtree(os.path.join(out_aprx, temp_name), ignore_errors=True)


########## ---------- MAIN ---------- ##########
try:

    # Create APRX
    os.makedir("temp")
    arcpy.CreateFileGDB_management(out_aprx, temp_name)
    arcpy.env.workspace = os.path.join(out_aprx, temp_name)
    Workspace = arcpy.env.workspace

    # Get template APRX
    aprx1 = arcpy.mp.ArcGISProject(in_aprx)

    # Processing
    StartTime = time.time()

    try:

        # Output files
        out_aprx_file = os.path.join(out_aprx, out_filename + ".aprx")
        out_png_file = os.path.join(out_png, out_filename + ".png")
        if os.path.exists(out_aprx_file) or os.path.exists(out_png_file):
            print("Output APRX and/or PNG already exists.")
            print("Please delete them or set overwrite to True and run the script again.")
            sys.exit(0)

        # Create map
        else:
            print("Creating map: " + out_filename)
            aprx1.saveACopy(out_aprx_file)
            aprx = arcpy.mp.ArcGISProject(out_aprx_file)
            m = aprx.listMaps()[0]
            lyt = aprx.listLayouts()[0]

            # Plot raster layer
            lyr = m.addDataFromPath(in_tif)
            lyr0 = m.listLayers()[0]
            tif_lyr = arcpy.ApplySymbologyFromLayer_management(lyr0, os.path.join(sym_tif))

            # Zoom to layer
            mf = lyt.listElements('MAPFRAME_ELEMENT','*')[0]
            mf.camera.setExtent(mf.getLayerExtent(lyr0,True,True))
            mf.zoomToAllLayers()

            # # Custom symbol for stretched raster
            # cim_lyr = lyr0.getDefinition('V2') 
            # colorizer = cim_lyr.colorizer
            # colorizer.customStretchMin = 0
            # colorizer.customStretchMax = 100
            # colorizer.stretchClasses = [
            #     {
            #         "type" : "CIMRasterStretchClass",
            #         "label" : 0,
            #         "value" : 100
            #     },
            #     {
            #         "type" : "CIMRasterStretchClass",
            #         "label" : 100,
            #         "value" : 100
            #     }
            # ]
            # lyr0.setDefinition(cim_lyr)

            # Update text
            for elm in lyt.listElements("TEXT_ELEMENT"):
                if elm.text == "map_title":  # Template aprx should contain a text box with the text: map_title
                    elm.text = "INSERT MAP TITLE HERE"

            # Export
            print("Exporting...")
            aprx.save()
            lyt.exportToPNG(out_png_file)

    except:
        print("Processing error...")
        traceback.print_exc()

    arcpy.ResetEnvironments()
    del arcpy
    shutil.rmtree(os.path.join(out_aprx, temp_name), ignore_errors = True)

    EndTime = time.time()
    print("Completed in ~ %s seconds" % round((EndTime - StartTime, 1)))

except:
    shutil.rmtree(os.path.join(out_aprx, temp_name), ignore_errors = True)
    traceback.print_exc()
