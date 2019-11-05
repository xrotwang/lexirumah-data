import geopy
import geopy.geocoders as gc
from geopy.distance import vincenty as distance
from pycldf import Wordlist
from clldutils.path import Path

import json
import urllib

from time import sleep
from pylexirumah import get_dataset

try:
    geonames_username = Path(__file__).parent.joinpath("username").open().read().strip()
    geonames = gc.GeoNames(username=geonames_username, timeout=None)
except FileNotFoundError:
    geonames = None
nominatim = gc.Nominatim(user_agent="lexirumah")

detail={"ID": ["ADM2", "ADM3"],
        "TL": []}

def get_region(latitude, longitude):
    return json.load(urllib.request.urlopen(
        "http://api.geonames.org/countrySubdivisionJSON?lat={lat:f}&lng={lng:f}&username={user:}&level=2".format(lat=latitude, lng=longitude, user=geonames_username)))
    return json.load(urllib.request.urlopen(
        "http://api.geonames.org/extendedFindNearbyJSON?lat={lat:f}&lng={lng:f}&username={user:}".format(lat=latitude, lng=longitude, user=geonames_username)))


def get_region(latitude, longitude):
    try:
        for_country = geonames.reverse(
            (latitude, longitude),
            exactly_one=False)[0]
    except geopy.exc.GeocoderServiceError:
        return None
    address = [for_country.raw["adminName1"], for_country.raw["countryName"]]
    country =  for_country.raw['countryCode']
    for d in detail[country.upper()]:
        try:
            if d == "ADM1":
                continue
            else:
                element = geonames.reverse(
                    (latitude, longitude),
                    feature_code=d,
                    find_nearby_type='findNearby',
                    exactly_one=False)[0]
            address.insert(0, element.raw["name"])
        except (geopy.exc.GeocoderServiceError, TypeError):
            continue
    return address

if __name__ == "__main__":
    data = get_dataset()
    lang = data["LanguageTable"]
    updated = []
    for language in lang.iterdicts():
        if not language["Latitude"]:
            updated.append(language)
            continue
        print(language["Name"])
        latlon = (language["Latitude"], language["Longitude"])
        print("{:10.5f} {:10.5f}".format(*latlon))
        region = get_region(*latlon)
        sleep(1)
        print(region)
        if not region:
            continue
        language["Region"] = ", ".join(region)
        updated.append(language)
    data.write(LanguageTable=updated)

