import os, argparse
import json, requests
import datetime
import pandas as pd


# Get inputs
parser = argparse.ArgumentParser()
parser.add_argument('--startdate', '-s', type=str)
parser.add_argument('--enddate', '-e', type=str)
parser.add_argument('--sentinel', type=str)
parser.add_argument('--cloud', type=float)
parser.add_argument('--path', type=str)
parser.add_argument('--username', '-u', type=str)
parser.add_argument('--password', '-p', type=str)
parser.add_argument('--geometry', '-g', type=str)
args = parser.parse_args()


# Credentials
def get_access_token(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
        }
    try:
        r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data=data,
        )
        r.raise_for_status()
    except Exception as e:
        raise Exception(
            f"Access token creation failed. Reponse from the server was: {r.json()}"
            )
    return r.json()["access_token"]
        
access_token = get_access_token(args.username, args.password)


# Search for images
startdate = datetime.datetime.strptime(args.startdate, '%Y%m%d').strftime('%Y-%m-%d')
enddate = datetime.datetime.strptime(args.enddate, '%Y%m%d').strftime('%Y-%m-%d')
cloud = args.cloud
data_collection = "SENTINEL-" + args.sentinel
with open(os.path.join(os.getcwd(), args.geometry)) as f:
    gj = json.load(f)
features = gj['features'][0]
coordinates = [str(xy[0]) + " " + str(xy[1]) for xy in features["geometry"]["coordinates"][0]]
polygon = "POLYGON(({}))".format(coordinates).replace("[","").replace("\'","").replace("]","")

json = requests.get(f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start gt {startdate}T00:00:00.000Z and ContentDate/Start lt {enddate}T00:00:00.000Z and\
                        Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {cloud}) and\
                            Collection/Name eq '{data_collection}' and\
                                OData.CSC.Intersects(area=geography'SRID=4326;{polygon}')").json()
img_list = pd.DataFrame.from_dict(json['value'])
print("Images found:", len(img_list))


# Download images
for i in range(len(img_list)):
    id = img_list.iloc[i, 1]
    name = img_list.iloc[i, 2].split(".SAFE")[0]
    url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({id})/$value"

    print("Downloading imagery:", name)

    headers = {"Authorization": f"Bearer {access_token}"}

    session = requests.Session()
    session.headers.update(headers)
    response = session.get(url, headers=headers, stream=True)

    file_path = os.path.join(os.getcwd(), args.path, name + ".zip")
    with open(file_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)

print("COMPLETED!")
