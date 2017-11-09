"""Plot the number of filled-in parameters for each language.

parameter_sampled: map languages to sets of parameters
"""

# CLI libraries
import sys
import argparse

# Plotting libraries
import numpy
import colorsys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

# Libraries for accessing Glottolog online
import re
import json
from urllib.request import urlopen
from urllib.error import HTTPError

# CLDF libraries
import pycldf
from util import get_dataset, Path

# Try to use local Glottolog
try:
    from pyglottolog.api import Glottolog
    glottolog = Glottolog()
    languoid = glottolog.languoid
except ImportError:
    languoid = None


def online_languoid(iso_or_glottocode):
    """Look the glottocode or ISO-639-3 code up in glottolog online.

    Return a Namespace object with attributes corresponding to the JSON API
    dictionary keys. Return None if the code is invalid, no matter whether it
    is well-formatted (but unused) or not.

    Parameters
    ----------
    iso_or_glottocode: str
        A three-letter ISO-639-3 language identifier or a four-letter-four-digit
        Glottolog language identifier.

    Returns
    -------
    Namespace or None

    """
    if re.fullmatch("[a-z]{3}", glottocode):
        try:
            data = json.loads(urlopen(
                "http://glottolog.org/resource/languoid/iso/{:}.json".format(glottocode)
            ).read().decode('utf-8'))
        except HTTPError:
            return None
    elif re.fullmatch("[a-z]{4}[0-9]{4}"):
        try:
            data = json.loads(urlopen(
                "http://glottolog.org/resource/languoid/id/{:}.json".format(glottocode)
            ).read().decode('utf-8'))
        except HTTPError:
            return None
    else:
        return None
    language = argparse.Namespace()
    for key, val in data.items():
        setattr(language, key, val)
    return language


def parameters_sampled(dataset):
    """Check which parameters are given for which languages.

    Return the dictionary mapping all language ids present in the dataset's
    primary table to the set of parameter ids with values for that language.

    Parameters
    ----------
    dataset: pycldf.Dataset

    Returns
    -------
    dict

    """
    primary = dataset.primary_table
    languageReference = dataset[primary, "languageReference"].name
    parameterReference = dataset[primary, "parameterReference"].name
    sampled = {}
    for row in dataset["FormTable"].iterdicts():
        sampled.setdefault(row[languageReference], set()).add(row[parameterReference])
    return sampled


def main(args=sys.argv):
    """The main CLI"""
    # Parse options
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        'dataset', type=Path,
        help="Path to the CLDF dataset (metadata json or metadata-free csv)")
    parser.add_argument(
        "output",
        help="File name to write output to")
    parser.add_argument(
        "--online", action="store_true", default=False,
        help="Use glottolog.org as source for coordinates, not a local clone")
    options = parser.parse_args()

    if options.online:
        languoid = online_languoid

    # Open the dataset
    dataset = get_dataset(options.dataset)

    # Read which language has which parameters given
    sampled = parameters_sampled(dataset)

    # Try to load language locations from the dataset
    locations = {}
    try:
        idcol = dataset["LanguageTable", "id"].name
        latcol = dataset["LanguageTable", "latitude"].name
        loncol = dataset["LanguageTable", "longitude"].name
        for row in dataset["LanguageTable"].iterdicts():
            locations[row[idcol]] = row[latcol], row[loncol]
    except ValueError:
        # No language table
        pass

    # Aggregate the data
    lats, lons, sizes = [], [], []

    for language, parameters in sampled.items():
        try:
            lat, lon = locations[language]
        except KeyError:
            # Try to find the location on Glottolog
            try:
                lang = languoid(language)
                lat, lon = lang.latitude, lang.longitude
            except TypeError:
                # languoid function is None
                continue
            except AttributeError:
                # language not found: None was returned, which has no lat/lon
                continue
        try:
            lats.append(float(lat))
        except TypeError:
            continue
        lons.append(float(lon))
        sizes.append(len(parameters))

    assert len(sizes) == len(lats) == len(lons)

    # Calculate coordinate boundaries
    min_lat, max_lat = min(lats), max(lats)
    d_lat = max_lat - min_lat
    min_lat = max(-90, min_lat - 0.1 * d_lat)
    max_lat = min(90, max_lat + 0.1 * d_lat)

    min_lon, max_lon = min(lons), max(lons)
    d_lon = max_lon - min_lon
    min_lon = max(-180, min_lon - 0.1 * d_lon)
    max_lon = min(180, max_lon + 0.1 * d_lon)

    # Draw the base map
    # TODO: Get coordinates from commandline, fallback to bounding box of data
    # TODO: Give more control over map drawing to user
    map = Basemap(llcrnrlat=min_lat, urcrnrlat=max_lat, llcrnrlon=min_lon, urcrnrlon=max_lon,
                  # projection='lcc',
                  resolution='h', area_thresh=10)
    # TODO: Add switch for drawing other patterns (countries, eg.)
    map.drawcoastlines()
    # TODO: Override color from command line
    map.fillcontinents(color='#fff7ee', zorder=0)

    # Plot the vocabulary sizes
    # TODO: get colormap from command line
    map.scatter(lons, lats, c=sizes, cmap=plt.get_cmap("magma_r"), latlon=True)

    # TODO: Improve shape of components: Colorbar is very huge, margins are quite large
    plt.colorbar()
    plt.gcf().set_size_inches(12, 9)

    plt.savefig(options.output)
    return 0

if __name__ == "__main__":
    main(sys.argv)




