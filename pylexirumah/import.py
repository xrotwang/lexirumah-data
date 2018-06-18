#!/usr/bin/env python

import sys
import argparse
import itertools
from collections import OrderedDict
from clldutils.path import Path

import csvw
import xlrd
import pycldf

from pylexirumah import (get_dataset, repository)

parser = argparse.ArgumentParser(description="Import word lists from a new source into LexiRumah.")
parser.add_argument("directory", nargs="?",
                    type=Path, default="./",
                    help="The folder containing the wordlist description,"
                    " derived from the standard template. (default: The"
                    " current working directory.)")
parser.add_argument("--wordlist",
                    type=Path, default=repository,
                    help="The Wordlist to expand. (default: LexiRumah.)")
args = parser.parse_args()

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
                rows.__enter__()
                def value(cell):
                    return cell
                return rows, value
            raise ValueError("Wordlist file found, but no valid file type.")
    raise ValueError("No valid wordlist file found.")


print("Loading the existing language metadata, to be merged ...")
languages = OrderedDict(
    (lang["ID"], lang)
    for lang in dataset["LanguageTable"].iterdicts())

print("Loading the new language metadata from your directory ...")
rows, value = read_newest_table(
    args.directory / "4 - language metadata", "lects")
for r, row in enumerate(rows):
    if r == 0:
        columns = [value(x) for x in row]
    else:
        lang = {c: value(v) for c, v in zip(columns, row)}
        if lang["ID"] == "abui1241-lexi":
            # Example language, skip
            continue
        print("Found new language {:}.".format(lang["ID"]))
        languages[lang["ID"]] = lang

print("Write all languages, old and new, back to file ...")
dataset["LanguageTable"].write(languages.values())

print("Language metadata merged.")


print("Loading the existing sources ...")
sources = dataset.sources

print("Investigating new sources ...")
source_description = changed_files(
    args.directory / "3 - normalized metadata of original source")[0]
new_sources = [
    source
    for source in pycldf.sources.Sources.from_file(source_description)
    if source.id not in {
            "glottolog", "abvd", "fieldwork_abui_lexirumah",
            "greenbook_proto_AP_tsv", "fricke2014topics", "said1977bugis",
            "samely2013kedang", "550122", "fricke2014hewa"}]

if not new_sources:
    raise ValueError("No sources for this word list found."
                     " I looked in your newest file, {:}".format(
                         source_description))

new_sources_field = [source.id for source in new_sources]
print("Found new source(s) {:}."
      " I assume this applies to all entries in this wordlist.".format(
          "; ".join(new_sources_field)))

print("Writing all sources, old and new, back to file ...")
for source in new_sources:
    dataset.sources.add(source)
dataset.write_sources()

print("Loading existing forms from previous wordlists ...")
forms = dataset["FormTable"]
all_rows = list(dataset["FormTable"].iterdicts())
old_forms = len(all_rows)

print("Preparing to load additional forms from new wordlist ...")
max_id = max(row["ID"] for row in all_rows)
copy_columns = ["Concept_ID", "Lect_ID", "Form", "Segments", "Comment"]
table_columns = [column.name for column in forms.tableSchema.columns]

print("Reading forms ...")
rows, value = read_newest_table(
    args.directory / "5 - wordlist created from original source", "wordlist")
for r, row in enumerate(rows):
    if r == 0:
        columns = [value(x) for x in row]
        indices = [columns.index(c)
                   for c in copy_columns]
        previous_lect = None
        previous_concept = None
        continue
    values = [value(row[index]) for j, index in enumerate(indices)]

    new_entry = {c: None for c in table_columns}
    new_entry.update({c: v for c, v in zip(copy_columns, values)})
    if not new_entry["Concept_ID"]:
        new_entry["Concept_ID"] = previous_concept
    previous_concept = new_entry["Concept_ID"]

    if not new_entry["Lect_ID"]:
        new_entry["Lect_ID"] = previous_lect
    previous_lect = new_entry["Lect_ID"]
    new_entry['ID'] = max_id + r

    if new_entry["Form"] or new_entry["Comment"] or new_entry["Segments"]:
        if new_entry["Form"] and not new_entry["Segments"]:
            # FIXME: Look up the orthographic profile in the source metadata!
            # FIXME: Segment cleanly!
            new_entry["Segments"] = " ".join(new_entry["Form"])
        if not new_entry["Form"] and new_entry["Segments"]:
            new_entry["Form"] = "".join(new_entry["Segments"].split(" "))
        if new_entry["Segments"]:
            new_entry["Segments"] = new_entry["Segments"].split(" ")
    else:
        continue

    if new_entry["Lect_ID"] not in languages:
        raise ValueError(
            "No metadata found for lect {:s} of form in line {:d}.".format(
                new_entry["Lect_ID"], r))

    new_entry["Source"] = new_sources_field

    all_rows.append(new_entry)

print("Found {:d} new forms.".format(len(all_rows) - old_forms))

print("Writing all forms, old and new, back to file ...")
forms.write(all_rows)
print("Word list data merged.")
