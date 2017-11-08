"""Plot the number of filled-in parameters for each language.

parameter_sampled: map languages to sets of parameters
"""

import sys
import argparse
import os.path

import numpy

import colorsys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

import pycldf
from util import get_dataset


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
    parser.add_argument('dataset')
    options = parser.parse_args()

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
            ...
            continue
        try:
            lats.append(float(lat))
            lons.append(float(lon))
        except TypeError:
            continue
        sizes.append(len(parameters))

    print(lats, lons, sizes)
    # Draw the base map
    # TODO: Get size from data
    # TODO: Get coordinates from commandline, fallback to bounding box of data
    map = Basemap(projection='lcc', width=700000, height=400000, lat_0=-9, lat_1=-11, lon_0=125, lon_1=129, resolution='h', area_thresh=10)
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

    # TODO: Take from user where to write output to, with a reasonable default
    # ("Migration" isn't reasonable)
    plt.savefig("migration.png")
    plt.savefig("migration.pdf")
    return 0

if __name__ == "__main__":
    main(sys.argv)




