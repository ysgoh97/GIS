"""
Arcpy script to plot shapefile and raster

Author: Yun Si
Last modified: 20240613
Tested on: ArcMap 10.7.1 & Python 2.7
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
in_shp = os.path.join(cwd, "Input", "shapefile.shp")

# Input template map
in_mxd = os.path.join(cwd, "Template", "MXD", "map.mxd")

# Input template symbology
sym_tif = os.path.join(cwd, "Template", "LYR", "raster.lyr")
sym_shp = os.path.join(cwd, "Template", "LYR", "shapefile.lyr")

# Output directory
out_mxd = os.path.join(cwd, "Output", "MXD")
out_png = os.path.join(cwd, "Output", "PNG")
out_filename = "out"


########## ---------- SYS CHECK ---------- ##########
if not os.path.exists(out_mxd):
    os.mkdir(out_mxd)
elif overwrite and os.path.exists(out_mxd):
    os.remove(os.path.join(out_mxd, out_filename + ".mxd"))

if not os.path.exists(out_png):
    os.mkdir(out_png)
if overwrite and os.path.exists(out_png):
    os.remove(os.path.join(out_png, out_filename + ".png"))

temp_name = "Working.gdb"
arcpy.env.overwriteOutput = overwrite
if os.path.exists(os.path.join(out_mxd, temp_name)):
    shutil.rmtree(os.path.join(out_mxd, temp_name), ignore_errors=True)


########## ---------- FUNCTIONS ---------- #################### ---------- SYS CHECK ---------- ##########
def plot_tif(tif_path, tif_sym_path, plot_df):
    fname = tif_path.split("\\")[-1].split(".tif")[0]
    arcpy.MakeRasterLayer_management(tif_path, fname)
    lyr = arcpy.mapping.Layer(fname)
    arcpy.mapping.AddLayer(plot_df, lyr, "TOP")
    lyr_sym = arcpy.mapping.Layer(tif_sym_path)
    lyr_update = arcpy.mapping.ListLayers(mxd, fname, plot_df)[0]
    arcpy.mapping.UpdateLayer(plot_df, lyr_update, lyr_sym, "TOP")
    return(fname)

def plot_shp(shp_path, shp_sym_path, plot_df):
    fname = shp_path.split("\\")[-1].split(".tif")[0]
    lyr = arcpy.mapping.Layer(shp_path)
    arcpy.mapping.AddLayer(plot_df, lyr, "TOP")
    lyr_sym = arcpy.mapping.Layer(shp_sym_path)
    lyr_update = arcpy.mapping.ListLayers(mxd, fname, plot_df)[0]
    arcpy.mapping.UpdateLayer(plot_df, lyr_update, lyr_sym, "TOP")
    return(fname)

########## ---------- MAIN ---------- ##########
try:

    # Create MXD
    os.makedir("temp")
    arcpy.CreateFileGDB_management(out_mxd, temp_name)
    arcpy.env.workspace = os.path.join(out_mxd, temp_name)
    Workspace = arcpy.env.workspace

    # Get template MXD
    mxd1 = arcpy.mapping.MapDocument(in_mxd)

    # Processing
    StartTime = time.time()

    try:

        # Output files
        out_mxd_file = os.path.join(out_mxd, out_filename + ".mxd")
        out_png_file = os.path.join(out_png, out_filename + ".png")
        if os.path.exists(out_mxd_file) or os.path.exists(out_png_file):
            print("Output MXD and/or PNG already exists.")
            print("Please delete them or set overwrite to True and run the script again.")
            sys.exit(0)

        # Create map
        else:
            print("Creating map: " + out_filename)
            mxd1.saveACopy(out_mxd_file)
            mxd = arcpy.mapping.MapDocumnet(out_mxd_file)
            main_df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]  # Main map in template mxd should be named "Layers"
            mini_df = arcpy.mapping.ListDataFrames(mxd, "MiniMap")[0]  # Mini map in template mxd should be named "MiniMap"

            # Plot
            tif_fname = plot_tif(in_tif, sym_tif, main_df)  # Plot raster in main map
            shp_fname = plot_shp(in_shp, sym_shp, mini_df)  # Plot shapefile in mini map

            # Set transparency
            lyr_tif = arcpy.mapping.ListLayers(mxd, tif_fname, main_df)[0]
            lyr_tif.transparency = 50

            # Turn on labels
            lyr_shp = arcpy.mapping.ListLayers(mxd, shp_fname, mini_df)[0]
            lyr_shp.showLabels = True
            lyr_shp_labelclass = lyr_shp.labelClasses[0]
            lyr_shp_labelclass.expression = '"{}" + "{}" + {Label} + "{}"+ "{}"'.format(
                "<FNT size = '16'>",
                "CLR red = '255' green = '0' blue = '0'>",
                "</CLR>",
                "</FNT>"
            )

            # Update text
            for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
                if elm.text == "map_title":  # Template mxd should contain a text box with the text: map_title
                    elm.text = "INSERT MAP TITLE HERE"

            # Export
            print("Exporting...")
            mxd.save()
            arcpy.mapping.ExportToPNG(mxd, out_png_file)

    except:
        print("Processing error...")
        traceback.print_exc()

    arcpy.ResetEnvironments()
    del arcpy
    shutil.rmtree(os.path.join(out_mxd, temp_name), ignore_errors = True)

    EndTime = time.time()
    print("Completed in ~ %s seconds" % round((EndTime - StartTime, 1)))

except:
    shutil.rmtree(os.path.join(out_mxd, temp_name), ignore_errors = True)
    traceback.print_exc()
    