#!/usr/bin/env python

"""Convert between LingPy and CLDF formats"""

import bisect

import sys

import csv

import pycldf.dataset
from clldutils.clilib import ArgumentParser

def cldf_to_lingpy(columns, replacement={
        'Parameter_ID': 'CONCEPT',
        'Language_ID': 'DOCULECT',
        'Cognateset_ID': 'COGID',
        'Form': 'IPA',
        'ID': 'REFERENCE',
        'Segments': 'TOKENS'}):
    """Turn CLDF column headers into LingPy column headers."""
    if type(columns) == str:
        return replacement.get(columns, columns.upper())
    columns = [replacement.get(c, c.upper()) for c in columns]
    return columns


def lingpy_to_cldf(columns, replacement={
        'REFERENCE': 'ID',
        'CONCEPT': 'Parameter_ID',
        'DOCULECT': 'Language_ID',
        'COGID': 'Cognate_Set',
        'IPA': 'Value',
        'TOKENS': 'Segments'}):
    """Turn LingPy column headers into CLDF column headers."""
    if type(columns) == str:
        return replacement.get(columns, columns.title())
    columns = [replacement.get(c, c.title()) for c in columns]
    return columns


def no_separators_or_newlines(string, separator="\t"):
    if separator == "\t":
        string = string.replace("\n", " ")
        return string.replace("\t", " ")
    elif separator == ",":
        string = string.replace("\n", "\t")
        return string.replace(",", ";")
    else:
        string = string.replace("\n", "\t")
        return string.replace(separator, "\t")


FIRSTCOLS = ["ID"]

def cldf(args):
    """Load a CLDF dataset and turn it into a LingPy word list file

    Sort by cognateset, for easier visual inspection of certain things I'm
    interested in.

    """
    input, output = args.args
    max_id = 0
    cogids = {None: 0}
    dataset = pycldf.dataset.Wordlist.from_metadata(input)
    primary_table = dataset[dataset.primary_table]
    try:
        cognate_set_iter = dataset["CognateTable"].iterdicts()
    except KeyError:
        cognate_set_iter = []
    cognate_set = {}
    for row in cognate_set_iter:
        row["COGNATESETTABLE_ID"] = row.pop("ID")
        form = row.pop("Form_ID")
        cognate_set[form] = row
    all_rows = []
    cognate_codes = []
    for i, row in enumerate(primary_table.iterdicts()):
        row.update(cognate_set.get(row["ID"], {}))
        o_row = {}
        for key, value in row.items():
            if isinstance(value, str):
                # Strings need special characters removed
                o_row[cldf_to_lingpy(key)] = no_separators_or_newlines(value)
            else:
                try:
                    # Sequences (Alignment, Segments) need conversion and
                    # special characters removed
                    o_row[cldf_to_lingpy(key)] = no_separators_or_newlines(
                        " ".join(value))
                except TypeError:
                    # Other values are taken as-is
                    o_row[cldf_to_lingpy(key)] = value
        o_row["ID"] = i + 1
        o_row.setdefault("COGID", cogids.setdefault(row.get("Cognateset_ID"), len(cogids)))
        all_rows.append(o_row)

        if i == 0:
            writer = csv.DictWriter(
                open(output, 'w'), delimiter="\t",
                fieldnames=sorted(o_row.keys(), key=lambda x: x not in FIRSTCOLS))
            writer.writeheader()
    try:
        all_rows = sorted(all_rows, key=lambda row: row["COGID"])
    except TypeError:
        # Incomparable COGIDs?
        pass
    for row in all_rows:
        writer.writerow(row)


def lingpy(args):
    input, output = args.args
    reader = csv.DictReader(input, delimiter="\t")
    for i, row in enumerate(reader):
        if i == 0:
            writer = csv.DictWriter(
                output, delimiter=",",
                fieldnames=[
                    lingpy_to_cldf(c)
                    for c in reader.fieldnames])
            writer.writeheader()
        writer.writerow({
            lingpy_to_cldf(key): value
            for key, value in row.items()})


if __name__ == "__main__":
    parser = ArgumentParser('lingpycldf', cldf, lingpy)
    sys.exit(parser.main())
