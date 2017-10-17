#!/usr/bin/env python

"""Convert between LingPy and CLDF formats"""

import sys

import csv

import pycldf.dataset
from clldutils.clilib import ArgumentParser

def cldf_to_lingpy(columns, replacement={
        'Parameter_ID': 'CONCEPT',
        'Language_ID': 'DOCULECT',
        'Cognate_set_ID': 'COGID',
        'Value': 'IPA',
        'Segments': 'TOKENS'}):
    """Turn CLDF column headers into LingPy column headers."""
    if type(columns) == str:
        return replacement.get(columns, columns.upper())
    columns = [replacement.get(c, c.upper()) for c in columns]
    return columns


def lingpy_to_cldf(columns, replacement={
        'ID': 'ID',
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
    """Load a CLDF dataset and turn it into a LingPy word list file"""
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
        form = row.pop("Form_ID")
        cognate_set[form] = row
    for i, row in enumerate(primary_table.iterdicts()):
        row.update(cognate_set.get(row["ID"], {}))
        if i == 0:
            writer = csv.DictWriter(
                open(output, 'w'), delimiter="\t",
                fieldnames=FIRSTCOLS + [
                    cldf_to_lingpy(c)
                    for c in row.keys()
                    if cldf_to_lingpy(c) not in FIRSTCOLS])
            writer.writeheader()
        o_row = {}
        for key, value in row.items():
            if isinstance(value, str):
                o_row[cldf_to_lingpy(key)] = no_separators_or_newlines(value)
            else:
                try:
                    o_row[cldf_to_lingpy(key)] = no_separators_or_newlines(
                        " ".join(value))
                except TypeError:
                    o_row[cldf_to_lingpy(key)] = value
        try:
            o_row["ID"] = int(o_row["ID"])
        except (KeyError, ValueError):
            o_row["ID"] = max_id + 1
        max_id = max(max_id, o_row["ID"])
        o_row.setdefault("COGID", cogids.setdefault(
            row["Cognate_set_ID"], len(cogids)))
        writer.writerow(o_row)


def cldfwordlist(args):
    input, output = args.args
    max_id = 0
    reader = csv.DictReader(open(input), delimiter=",")
    cogids = {None: 0}
    for i, row in enumerate(reader):
        if i == 0:
            writer = csv.DictWriter(
                open(output, 'w'), delimiter="\t",
                fieldnames=FIRSTCOLS + [
                    cldf_to_lingpy(c)
                    for c in reader.fieldnames
                    if cldf_to_lingpy(c) not in FIRSTCOLS])
            writer.writeheader()
        o_row = {
            cldf_to_lingpy(key): no_separators_or_newlines(value)
            for key, value in row.items()}
        try:
            o_row["ID"] = int(o_row["ID"])
        except (KeyError, ValueError):
            o_row["ID"] = max_id + 1
        max_id = max(max_id, o_row["ID"])
        o_row.setdefault("COGID", cogids.setdefault(
            row["Cognate_set_ID"], len(cogids)))
        writer.writerow(o_row)


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
    parser = ArgumentParser('lingpycldf', cldf, cldfwordlist, lingpy)
    sys.exit(parser.main())
