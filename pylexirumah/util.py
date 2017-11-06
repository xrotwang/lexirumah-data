import re
import math

import csv
import json

import sys
import argparse

from clldutils.path import Path
from pycldf.sources import Source
from pycldf.dataset import Wordlist
from clldutils.csvw.metadata import Column

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

