import os, sys, shutil
import pandas as pd
import numpy as np
import arcpy
cwd = sys.path[0]


##### INPUT #####
in_stats_file = arcpy.GetParameterAsText(0)
in_raster_file = arcpy.GetParameterAsText(1)
out_raster_dir  = arcpy.GetParameterAsText(2)
out_raster_name  = arcpy.GetParameterAsText(3)
    
bands_no = 5
bands_list = [1, 2, 3, 4, 5]


##### SYS CHECK #####
if not os.path.exists(in_stats_file):
    print(in_stats_file + " does not exist. please try again...")
    sys.exit(0)
if not os.path.exists(in_raster_file):
    print(in_raster_file + " does not exist. please try again...")
    sys.exit(0)
if not os.path.exists(out_raster_dir):
    print(out_raster_dir + " does not exist. please try again...")
    sys.exit(0)
if os.path.exists(os.path.join(out_raster_dir, out_raster_name)):
    os.remove(os.path.join(out_raster_dir, out_raster_name))


##### GET BAND STATS #####
arcpy.AddMessage("Getting band statistics...")

table_indiv = False
table_cov = False

df_indiv = pd.DataFrame(index=bands_list, columns=['MIN', 'MAX', 'MEAN', 'STD'])
df_cov = pd.DataFrame(index=bands_list, columns=bands_list)

with open(in_stats_file) as f:
    for line, text in enumerate(f):
        
        if "STATISTICS of INDIVIDUAL LAYERS" in text:
            table_indiv = True
            table_indiv_line = line
        while table_indiv and line > table_indiv_line+1:
            if "#" not in text:
                text_split = text.split()
                df_indiv.loc[int(text_split[0]), 'MIN'] = float(text_split[1])
                df_indiv.loc[int(text_split[0]), 'MAX'] = float(text_split[2])
                df_indiv.loc[int(text_split[0]), 'MEAN'] = float(text_split[3])
                df_indiv.loc[int(text_split[0]), 'STD'] = float(text_split[4])
            break
        if "=" in text:
            table_indiv = False
            df_indiv['VAR'] = df_indiv['STD'] * df_indiv['STD']
                
        if "COVARIANCE MATRIX" in text:
            table_cov = True
            table_cov_line = line
        while table_cov and line > table_cov_line+1:
            if "#" not in text:
                text_split = text.split()
                df_cov.loc[int(text_split[0]), 1] = float(text_split[1])
                df_cov.loc[int(text_split[0]), 2] = float(text_split[2])
                df_cov.loc[int(text_split[0]), 3] = float(text_split[3])
                df_cov.loc[int(text_split[0]), 4] = float(text_split[4])
                df_cov.loc[int(text_split[0]), 5] = float(text_split[5])
            break
        if "=" in text:
            table_cov = False


##### CALCULATE WATER DEPTH-INVARIANT INDEX #####
temp_name = "Working.gdb"
temp_folder = cwd + "\\TempGDB"
if os.path.exists(temp_folder):
    shutil.rmtree(temp_folder)
os.makedirs(temp_folder)
arcpy.CreateFileGDB_management(temp_folder, temp_name)
arcpy.env.workspace = os.path.join(temp_folder, temp_name)
arcpy.env.overwriteOutput = True

for i in range(1, bands_no+1):
    arcpy.AddMessage("Transforming band {}...".format(i))
    arcpy.MakeRasterLayer_management(in_raster_file, "band_{}".format(i), "", "", str(i))
    arcpy.CopyRaster_management("band_{}".format(i), "%workspace%\\band_{}".format(i))
    arcpy.gp.RasterCalculator_sa("Ln(\"%workspace%\\band_{}\")".format(i), "%workspace%\\ln_band_{}".format(i))

arcpy.AddMessage("Calculating water depth-invariant index...")
for i in range(1, bands_no+1):
    for j in range(1, bands_no+1):
        if i<j:
            arcpy.AddMessage("Calculating index_{}_{}...".format(i, j))
            var_i = df_indiv.loc[i, 'VAR']
            var_j = df_indiv.loc[j, 'VAR']
            cov_ij = df_cov.loc[i, j]
            a_ij = (var_i - var_j) / (2*cov_ij)
            ki_kj = a_ij + np.sqrt((a_ij * a_ij + 1))
            arcpy.AddMessage("\tvar_i: " + str(var_i))
            arcpy.AddMessage("\tvar_j: " + str(var_j))
            arcpy.AddMessage("\tcov_ij: " + str(cov_ij))
            arcpy.AddMessage("\ta_ij: " + str(a_ij))
            arcpy.AddMessage("\tki_kj: " + str(ki_kj))
            arcpy.gp.RasterCalculator_sa("\"%workspace%\\ln_band_{}\" - ({} * \"%workspace%\\ln_band_{}\")".format(i, ki_kj, j), "%workspace%\\index_{}_{}".format(i, j))

arcpy.AddMessage("Creating band composite...")    
raster_list = arcpy.ListRasters()
raster_list_filter = [raster for raster in raster_list if "ln_band" not in raster]
raster_list_filter.sort()
raster_list_str = ""
for raster in raster_list_filter:
    raster_list_str += "{};".format(raster)
arcpy.CompositeBands_management(raster_list_str, "%workspace%\\Composite")

if os.path.exists(os.path.join(out_raster_dir, out_raster_name)):
    os.remove(os.path.join(out_raster_dir, out_raster_name))
arcpy.CopyRaster_management("%workspace%\\Composite", os.path.join(out_raster_dir, out_raster_name))

mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
addLayer = arcpy.mapping.Layer(out_raster_name)
arcpy.mapping.AddLayer(df, addLayer, "TOP")
arcpy.RefreshActiveView()
arcpy.RefreshTOC()

arcpy.AddMessage("Cleaning temporary data...")    
for raster in raster_list:
    arcpy.Delete_management(raster)
shutil.rmtree(temp_folder)
