#!/usr/bin/env python

"""Convert between LingPy and CLDF headers"""

import csv

import sys
import argparse


def cldf_to_lingpy(columns, replacement={
        'Parameter_ID': 'CONCEPT',
        'Language_ID': 'DOCULECT',
        'Cognate_Set': 'COGID',
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


def no_separators_or_newlines(string, separator=","):
    if separator == "\t":
        string = string.replace("\n", " ")
        return string.replace("\t", " ")
    elif separator == ",":
        string = string.replace("\n", "\t")
        return string.replace(",", ";")
    else:
        string = string.replace("\n", "\t")
        return string.replace(separator, "\t")

parser = argparse.ArgumentParser()
parser.add_argument("input", nargs='?',
                    type=argparse.FileType('r'), default=sys.stdin)
parser.add_argument("output", nargs='?',
                    type=argparse.FileType('w'), default=sys.stdout)
parser.add_argument("--cldf-to-lingpy", action='store_true', default=False)
args = parser.parse_args()


max_id = 0
if args.cldf_to_lingpy:
    reader = csv.DictReader(args.input, delimiter=",")
    # Actually, check if there is a metadata file.
    firstcols = ["ID"]
    cogids = {None: 0}
    for i, row in enumerate(reader):
        if i == 0:
            writer = csv.DictWriter(
                args.output, delimiter="\t",
                fieldnames=firstcols + [
                    cldf_to_lingpy(c)
                    for c in reader.fieldnames
                    if cldf_to_lingpy(c) not in firstcols])
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
            row["Cognate_Set"], len(cogids)))
        writer.writerow(o_row)
else:
    reader = csv.DictReader(args.input, delimiter="\t")
    for i, row in enumerate(reader):
        if i == 0:
            writer = csv.DictWriter(
                args.output, delimiter=",",
                fieldnames=[
                    lingpy_to_cldf(c)
                    for c in reader.fieldnames])
            writer.writeheader()
        writer.writerow({
            lingpy_to_cldf(key): value
            for key, value in row.items()})
