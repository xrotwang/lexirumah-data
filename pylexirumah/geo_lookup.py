import geopy.geocoders as gc
from geopy.distance import vincenty as distance
from pycldf import Wordlist
from clldutils.path import Path

google_api_key = Path(__file__).parent.joinpath("api_key").open().read().strip()
google = gc.GoogleV3(api_key=google_api_key)
geolocators = [gc.Nominatim(), google,]

detail={"Indonesia": "administrative_area_level_3",
        "Timor-Leste": "administrative_area_level_1"}


def get_region(latitude, longitude):
    for i, candidate in enumerate(
            google.reverse((latitude, longitude), exactly_one=False)):
        if i == 1:
            best = candidate
        country = candidate.raw["address_components"][-1]["long_name"]
        if detail[country] in candidate.raw["address_components"][0]["types"]:
            return candidate
    try:
        return best
    except NameError:
        return candidate


if __name__ == "__main__":
    import sys
    lang = Wordlist.from_metadata(sys.argv[1])["LanguageTable"]
    for language in lang.iterdicts():
        if not language["Latitude"]:
            continue
        print(language["Name"])
        latlon = (language["Latitude"], language["Longitude"])
        print("{:10.5f} {:10.5f}".format(*latlon))
        region = get_region(*latlon)
        print("{:10.5f} {:10.5f}           {:10.5f}  {:s}".format(
            region.latitude, region.longitude,
            distance((region.latitude, region.longitude), latlon).kilometers,
            region.address))

