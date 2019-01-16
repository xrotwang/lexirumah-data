import re
import math
import collections

import csv
import json

import sys
import argparse

from clldutils.path import Path
from pycldf.sources import Source
from pycldf.dataset import Wordlist, Dataset
from csvw.metadata import Column

from urllib.error import HTTPError
from urllib.request import urlopen

import newick
from pybtex.database import BibliographyData, Entry
try:
    import pyglottolog
    local_glottolog = pyglottolog.Glottolog()
except (ValueError, ImportError):
    local_glottolog = None

from .geo_lookup import get_region
from . import get_dataset, repository

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


def languoid(iso_or_glottocode):
    """Look the glottocode or ISO-639-3 code up in glottolog.

    If a local installation of Glottolog is available through
    `pyglottolog.Glottolog()`, use that; otherwise resort to Glottolog online.
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
    if local_glottolog:
        language = local_glottolog.languoids_by_code().get(
            iso_or_glottocode)
        return language
    else:
        return online_languoid(iso_or_glottocode)


def clade_codes(glottolog_language):
    """Generate the set of all glottocodes in the clade.

    Given a Glottolog languoid object, iterate recursively through all
    children, adding their glottocodes to a set.

    Parameters
    ----------
    glottolog_language: pyglottolog.languoid.Languoid
        A glottolog languoid, ancestor of all languoids in a clade.

    Returns
    -------
    Set of str

    """
    all_codes = {glottolog_language.glottocode}
    for child in glottolog_language.children:
        all_codes |= clade_codes(child)
    return all_codes


def lexirumah_glottocodes(dataset=None):
    """Generate a dict associating LexiRumah IDs with Glottocodes

    Returns
    -------
    Dict of Str: Str

    """
    if dataset is None:
        dataset = get_dataset()
    result = {}
    for lect in dataset["LanguageTable"].iterdicts():
        g = None
        try:
            g = lect["Glottocode"]
        except KeyError:
            pass
        if g is None:
            g = re.match("[a-z]{4}[0-9]{4}", lect["ID"]).group()
        result[lect["ID"]] = g
    return result


def glottolog_clade(iso_or_glottocode, dataset=None):
    """List all LexiRumah lects belonging to a Glottolog clade.

    Return a list of all LexiRumah lect IDs that belong to a glottolog clade
    specified by Glottocode or ISO-639-3 code.

    Parameters
    ----------
    iso_or_glottocode: str
        A three-letter ISO-639-3 language identifier or a four-letter-four-digit
        Glottolog language identifier.

    Returns
    -------
    List of str

    """
    if dataset is None:
        dataset = get_dataset()

    lect = languoid(iso_or_glottocode)
    try:
        children_codes = clade_codes(lect)
    except AttributeError:
        tree = newick.loads(lect.newick)[0]
        children_codes = {re.findall("\[[a-z]{4}[0-9]{4}\]", t.name)[0][1:-1]
                          for t in tree.walk()}
    return {
        id
        for id, glottocode in lexirumah_glottocodes(dataset).items()
        if glottocode in children_codes}


def all_lects(dataset=None):
    if dataset is None:
        datase = get_dataset(Path(__file__).parent.parent /
                "cldf" / "Wordlist-metadata.json")


def cognate_sets(dataset, code_column=None, partial_cognates="exact"):
    """Load cognate codes from a CLDF.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Partial cognate codes are handled differently depending on the value of
    partial_cognates: "exact" (the default) or "intersection". A form with
    partial cognate classes '1 2' will be listed under class (1, 2) in "exact"
    mode and under both classes 1 and 2 in "intersection" mode.

    Parameters
    ----------
    dataset : pycldf.Wordlist
        CLDF Wordlist data set
    code_column : str
        The name of the column containing the cognate codes in the FormTable
        (default: check FormTable and CognateTable for a cognatesetReference)
    partial_cognates : {"exact", "intersection"}
        Partial cognates handling mode
        (default: "exact")

    Returns
    -------
    dict mapping Cognateset IDs to sets of Form IDs

    """
    data = collections.defaultdict(lambda: set())
    if code_column:
        cognate_column_in_form_table = True
    else:
        try:
            code_column = dataset["FormTable", "cognatesetReference"].name
            cognate_column_in_form_table = True
            # The form table contains cognate sets!
        except KeyError:
            cognatesets = collections.defaultdict(lambda: "?")
            try:
                form_reference = dataset["CognateTable", "formReference"].name
                code_column = dataset["CognateTable", "cognatesetReference"].name
            except KeyError:
                raise ValueError(
                    "Dataset {:} has no cognatesetReference column in its "
                    "primary table or in a separate cognate table. "
                    "Is this a metadata-free wordlist and you forgot to "
                    "specify code_column explicitly?".format(filename))
            for row in dataset["CognateTable"].iterdicts():
                cognatesets[row[form_reference]] = row[code_column]
            cognate_column_in_form_table = False

    form_column = dataset["FormTable", "id"].name

    if cognate_column_in_form_table:
        for row in dataset["FormTable"].iterdicts():
            if partial_cognates == "exact":
                try:
                    data[tuple(row[code_column])].add(row[form_column])
                except TypeError:
                    data[row[code_column]].add(row[form_column])
            else:
                for pcognateset in row[code_column]:
                    data[pcognateset].add(row[form_column])
    else:
        for form, cognateset in cognatesets.items():
            if partial_cognates == "exact":
                try:
                    data[tuple(cognateset)].add(form)
                except TypeError:
                    data[cognateset].add(form)
            else:
                for pcognateset in cognateset:
                    data[pcognateset].add(form)
    return data

