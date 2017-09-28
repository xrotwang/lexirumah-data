#!/usr/bin/env python

"""Convert between LingPy and CLDF headers"""

import csv

import sys
import argparse


def cldf_to_lingpy(columns, replacement={
        'Feature_ID': 'CONCEPT_ID',
        'Language_ID': 'DOCULECT_ID',
        'Cognate Set': 'COGNATE_SET',
        'English': 'CONCEPT',
        'Language name (-dialect)': 'DOCULECT'}):
    """Turn CLDF column headers into LingPy column headers."""
    if type(columns) == str:
        return replacement.get(columns, columns.upper())
    columns = [replacement.get(c, c.upper()) for c in columns]
    return columns


def lingpy_to_cldf(columns, replacement={
        'CONCEPT_ID': 'Feature_ID',
        'DOCULECT_ID': 'Language_ID',
        'COGNATE_SET': 'Cognate Set',
        'CONCEPT': 'English',
        'ASJP': 'ASJP',
        'IPA': 'IPA',
        'DOCULECT': 'Language name (-dialect)'}):
    """Turn CLDF column headers into LingPy column headers."""
    if type(columns) == str:
        return replacement.get(columns, columns.title())
    columns = [replacement.get(c, c.title()) for c in columns]
    return columns

parser = argparse.ArgumentParser()
parser.add_argument("input", nargs='?',
                    type=argparse.FileType('r'), default=sys.stdin)
parser.add_argument("output", nargs='?',
                    type=argparse.FileType('w'), default=sys.stdout)
parser.add_argument("--cldf-to-lingpy", action='store_true', default=False)
args = parser.parse_args()

reader = csv.DictReader(args.input, delimiter="\t")

if args.cldf_to_lingpy:
    firstcols = ["ID", "CONCEPT", "DOCULECT_ID", "IPA", "COGID"]
    cogids = {None: 0}
    for i, row in enumerate(reader):
        if i == 0:
            writer = csv.DictWriter(
                args.output, delimiter="\t",
                fieldnames=firstcols + [
                    cldf_to_lingpy(c)
                    for c in row.keys()
                    if cldf_to_lingpy(c) not in firstcols])
            writer.writeheader()
        o_row = {
            cldf_to_lingpy(key): value
            for key, value in row.items()}
        o_row.setdefault("ID", i)
        o_row.setdefault("COGID", cogids.setdefault(
            row["Group"], len(cogids)))
        writer.writerow(o_row)
else:
    writer = csv.DictWriter(args.output, delimiter="\t")
    for row in reader:
        writer.writerow({
            lingpy_to_cldf(key): value
            for key, value in row.items()})
