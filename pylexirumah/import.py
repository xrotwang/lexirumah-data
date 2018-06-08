#!/usr/bin/env python

import sys
import argparse
import itertools
from collections import OrderedDict
from pathlib import Path

import xlrd
import csvw

from pylexirumah.util import (get_dataset, lexirumah_glottocodes, repository)

parser = argparse.ArgumentParser(description="Import word lists from a new source into LexiRumah.")
parser.add_argument("directory", nargs="?",
                    type=Path, default="./",
                    help="The folder containing the wordlist description,"
                    " derived from the standard template. (default: The"
                    " current working directory.)")
parser.add_argument("--wordlist",
                    type=Path, default=repository,
                    help="The Wordlist to expand. (default: LexiRumah.)")
args = parser.parse_args(["../LanguageTemplate"])

dataset = get_dataset(args.wordlist)
if dataset.module != 'Wordlist':
    raise ValueError(
        "This script can only import wordlist data to a CLDF Wordlist.")

# Define how to find the relevant changed files
try:
    import pygit2
    def changed_files(path):
        ...
    raise NotImplementedError("No git support yet.")
except ImportError:
    print("WARNING: No pygit2 module found, relying on heuristics for finding"
          " your changes.",
          file=sys.stderr)
    def changed_files(path):
        if not path.exists():
            raise ValueError("Path {:} does not exist.".format(path))
        paths = sorted(path.glob("*"),
                       key=lambda p: p.lstat().st_mtime,
                       reverse=True)
        return paths


def read_newest_table(path, stem):
    for file in changed_files(path):
        if file.stem == stem:
            if file.suffix == ".xlsx":
                rows = xlrd.open_workbook(
                    str(file)).sheet_by_index(0).get_rows()
                def value(cell):
                    return cell.value
                return rows, value
            elif file.suffix == ".csv":
                rows = csvw.UnicodeReader(file.open())
                def value(cell):
                    return cell
                return rows, value
            raise ValueError("Wordlist file found, but no valid file type.")
    raise ValueError("No valid wordlist file found.")


# Load the metadata of the old languages
languages = OrderedDict(
    (lang["ID"], lang)
    for lang in dataset["LanguageTable"].iterdicts())

# Load the metadata of the new languages
rows, value = read_newest_table(
    args.directory / "4 - language metadata", "lects")
for r, row in enumerate(rows):
    if r == 0:
        columns = [value(x) for x in row]
    else:
        lang = {c: value(v) for c, v in zip(columns, row)}
        if lang["ID"] == "abui124-lexi":
            # Example language, skip
            continue
        languages[lang["ID"]] = lang

# Write all languages back to file
dataset["LanguageTable"].write(languages.values())

forms = dataset["FormTable"]
all_rows = list(dataset["FormTable"].iterdicts())

max_id = max(row["ID"] for row in all_rows)
copy_columns = ["Concept_ID", "Lect_ID", "Form", "Segments", "Comment"]
table_columns = [column.name for column in forms.tableSchema.columns]

rows, value = read_newest_table(
    args.path / "5 - wordlist created from original source", "wordlist")
for r, row in enumerate(rows):
    if r == 0:
        columns = [value(x) for x in row]
        indices = [columns.index(c)
                   for c in copy_columns]
        previous_lect = None
        previous_concept = None
        continue
    values = [value(row[index]) or previous_row[j]
                for j, index in enumerate(indices)]
    previous_concept = values[0]
    previous_lect = values[1]

    new_entry = {c: None for c in table_columns}
    new_entry.update({c: v for c, v in zip(copy_columns, values)})
    new_entry['ID'] = max_id + r
    all_rows.append(new_entry)

forms.write(all_rows)
