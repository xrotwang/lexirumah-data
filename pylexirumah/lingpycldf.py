#!/usr/bin/env python

"""Convert between LingPy and CLDF (pre-1.0 or Wordlist) formats"""

import bisect

import sys

import csv
import collections

import pycldf.dataset
from clldutils.clilib import ArgumentParser

def cldf_to_lingpy(columns, replacement={
        'Parameter_ID': 'CONCEPT',
        'Language_ID': 'DOCULECT',
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
    #TODO: Docstring missing.
    if separator == "\t":
        string = string.replace("\n", " ")
        return string.replace("\t", " ")
    elif separator == ",":
        string = string.replace("\n", "\t")
        return string.replace(",", ";")
    else:
        string = string.replace("\n", "\t")
        return string.replace(separator, "\t")


FIRSTCOLS = ["ID", "COGID"]


def cldf(args):
    """Load a CLDF dataset and turn it into a LingPy word list file

    Sort by cognateset, for easier visual inspection of certain things I'm
    interested in.
    """
    input, output = args.args
    max_id = 0
    cogids = {None: 0}
    dataset = pycldf.dataset.Wordlist.from_metadata(input)
    try:
        cognate_set_iter = dataset["CognateTable"].iterdicts()
    except KeyError:
        cognate_set_iter = []
    cognate_set = {}
    for cognate_table_row in cognate_set_iter:
        cognate_table_row["COGNATESETTABLE_ID"] = cognate_table_row.pop("ID")
        form = cognate_table_row.pop("Form_ID")
        cognate_set[form] = cognate_table_row

    all_rows = []
    cognate_codes = []
    for i, row in enumerate(dataset["FormTable"].iterdicts()):
        try:
            cognate_table_row = cognate_set[row["ID"]]
            row.update(cognate_table_row)
        except KeyError:
            pass

        o_row = collections.OrderedDict()
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
        if "COGID" not in o_row.keys():
            o_row["COGID"] =cogids.setdefault(row.get("Cognateset_ID"), len(cogids))
        all_rows.append(o_row)

        if i == 0:
            # Rearrange the headers so that 'ID' and 'COGID' are the first two columns.
            for header in reversed(FIRSTCOLS):
                o_row.move_to_end(header, last=False)
            writer = csv.DictWriter(
                open(output, 'w', encoding='utf-8'), delimiter="\t",
                fieldnames=o_row.keys())
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
