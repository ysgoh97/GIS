"""
References:

1. https://user.eumetsat.int/resources/user-guides/introductory-data-store-user-guide#ID-Authentication-and-log-in
2. https://user.eumetsat.int/resources/user-guides/eumetsat-data-access-client-eumdac-guide#ID-Quickstart-for-EUMDACs-Python-library
3. https://gitlab.eumetsat.int/eumetlab/data-services/eumdac_data_tailor/-/blob/master/1_Using_the_Data_Tailor_with_EUMDAC.ipynb?ref_type=heads

"""

import os, shutil
import json, requests
import eumdac
import datetime, time
import fnmatch

start_date = "20210401"
end_date = "20210430"
cur_dir = os.getcwd()
geometry = r"Template\map.geojson"
out_path = r"Downloads"


# API credentials
consumer_key = 'INSERT_KEY_HERE'
consumer_secret = 'INSERT_SECRET_HERE'
credentials = (consumer_key, consumer_secret)
token = eumdac.AccessToken(credentials)
#print(f"This token '{token}' expires {token.expiration}")
datastore = eumdac.DataStore(token)
#print(datastore.collections)


# Set imagery collection, sensing start and end time
selected_collection = datastore.get_collection('EO:EUM:DAT:0407')
start = datetime.datetime.strptime(start_date, '%Y%m%d')
end = datetime.datetime.strptime(end_date, '%Y%m%d')

# Set area
with open(os.path.join(cur_dir, geometry)) as f:
    gj = json.load(f)
features = gj['features'][0]
coordinates = [[xy[0], xy[1]] for xy in features["geometry"]["coordinates"][0]]


# Retrieve data that matches filter
products = selected_collection.search(
    geo='POLYGON(({}))'.format(','.join(["{} {}".format(*coord) for coord in coordinates])),
    dtstart=start, 
    dtend=end)
print(f'\nFound Datasets: {products.total_results} datasets for the given time range\n')


if products.total_results != 0:
    # Prioritize NT (non-critical time), only use NR (near real time) if NT unavailable
    # Get NT list (without product creation date)
    print("If Non-Critical Time dataset is available, only Non-Critical Time dataset will be downloaded.")
    print("If Non-Critical Time dataset is not available, Near Real Time dataset will be downloaded.\n")
    NT_list = []
    for product in products:
        with product.open() as fsrc:
            if "NT" in fsrc.name:
                NT_name = fsrc.name
                NT_name_split = NT_name.split("_")
                del NT_name_split[9]
                NT_list.append("_".join(NT_name_split))


    # Customize
    datatailor = eumdac.DataTailor(token)
    chain = eumdac.tailor_models.Chain(
        product='OLL2WFR',
        format='geotiff',
        projection="geographic",
        filter={"bands": ["tsm_nn"]}
    )

    count = 1
    for product in products:
        customisation  = datatailor.new_customisation(product, chain)

        # Prioritize NT (non-critical time), only use NR (near real time) if NT unavailable
        with product.open() as fsrc:
            product_name = fsrc.name
        product_name_split = product_name.split("_")
        if product_name_split[16] == "NT": 
            pass # If NT, continue to download NT
        else:
            product_name_split[16] = "NT"
            del product_name_split[9]
            if any("_".join(product_name_split) in x for x in NT_list):
                continue # If NR, but NT available, skip to next
            else:
                pass # If NR, and NT not available, download NR

        try:
            pass
            #print(f"Customisation {customisation._id} started.")
        except eumdac.datatailor.DataTailorError as error:
            print(f"Error related to the Data Tailor: '{error.msg}'")
        except requests.exceptions.RequestException as error:
            print(f"Unexpected error: {error}")

        status = customisation.status
        sleep_time = 10 # seconds

        # Customisation Loop
        while status:
            status = customisation.status

            if "DONE" in status:
                #print(f"Customisation {customisation._id} is successfully completed.")
                
                # Download
                try:
                    tif, = fnmatch.filter(customisation.outputs, '*.tif')
                    print(f'Downloading Sentinel-3 TSM imagery {count}: {os.path.splitext(product_name)[0] + ".tif"}')
                    with customisation.stream_output(tif,) as stream, \
                        open(os.path.join(cur_dir, out_path, os.path.splitext(product_name)[0] + ".tif"), mode='wb') as fdst:
                        shutil.copyfileobj(stream, fdst)
                        count+=1

                except eumdac.datatailor.CustomisationError as error:
                    print(f"Data Tailor Error", error)
                except requests.exceptions.RequestException as error:
                    print(f"Unexpected error: {error}")
                break

            elif status in ["ERROR","FAILED","DELETED","KILLED","INACTIVE"]:
                print(f"Customisation {customisation._id} was unsuccessful. Customisation log is printed.\n")
                print(customisation.logfile)
                break

            elif "QUEUED" in status:
                #print(f"Customisation {customisation._id} is queued.")
                pass
            elif "RUNNING" in status:
                #print(f"Customisation {customisation._id} is running.")
                pass
            time.sleep(sleep_time)

print("\nCOMPLETED!\n")
