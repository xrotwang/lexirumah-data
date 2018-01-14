import re
import math

import csv
import json

import sys
import argparse

from clldutils.path import Path
from pycldf.sources import Source
from pycldf.dataset import Wordlist, Dataset
from csvw.metadata import Column

from pyclpa.base import Sound
from segment import tokenize_clpa, CLPA

from geo_lookup import get_region
from pybtex.database import BibliographyData, Entry


# class C:
#     address = "ENUS"
# def get_region(lat, lon):
#     return C()


REPLACE = {
    " ": "_",
    '’': "'",
    '-': "_",
    '.': "_",
    "'": "'",
    "*": "",
    '´': "'",
    'µ': "_",
    'ǎ': "a",
    '̃': "_",
    ',': "ˌ",
    '=': "_",
    '?': "ʔ",
    'ā': "aː",
    "ä": "a",
    'Ɂ': "ʔ",
    "h̥": "h",
    "''": "'",
    "á": "'a",
    'ū': "uː",
}


def identifier(string):
    """Turn a string into a python identifier."""
    return re.sub('(\W|^(?=\d))+', '_', string).strip("_")


def resolve_brackets(string):
    """Resolve a string into all description without brackets

    For a `string` with matching parentheses, but without nested parentheses,
    yield every combination of the contents of any parenthesis being present or
    absent.

    >>> list(resolve_brackets("no brackets"))
    ["no brackets"]

    >>> sorted(list(resolve_brackets("(no )bracket(s)")))
    ["bracket", "brackets", "no bracket", "no brackets"]

    """
    if "(" in string:
        opening = string.index("(")
        closing = string.index(")")
        for form in resolve_brackets(string[:opening] + string[closing+1:]):
            yield form
        for form in resolve_brackets(string[:opening] + string[opening+1:closing] + string[closing+1:]):
            yield form
    else:
        yield string


def get_dataset(fname):
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    pycldf.Dataset
    """
    fname = Path(fname)
    if not fname.exists():
        raise FileNotFoundError(
            '{:} does not exist'.format(fname))
    if fname.suffix == '.json':
        return Dataset.from_metadata(fname)
    return Dataset.from_data(fname)


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
    if re.fullmatch("[a-z]{3}", iso_or_glottocode):
        try:
            data = json.loads(urlopen(
                "http://glottolog.org/resource/languoid/iso/{:}.json".format(
                    iso_or_glottocode)
            ).read().decode('utf-8'))
        except HTTPError:
            return None
    elif re.fullmatch("[a-z]{4}[0-9]{4}", iso_or_glottocode):
        try:
            data = json.loads(urlopen(
                "http://glottolog.org/resource/languoid/id/{:}.json".format(
                    iso_or_glottocode)
            ).read().decode('utf-8'))
        except HTTPError:
            return None
    else:
        return None
    language = argparse.Namespace()
    for key, val in data.items():
        setattr(language, key, val)
    return language
