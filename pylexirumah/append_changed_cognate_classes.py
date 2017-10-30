#!/usr/bin/env python3

"""Update cognate codes and alignments of a CLDF dataset from an Edictor file."""

import bisect
import itertools

from argparse import ArgumentParser, FileType

import csv
import datetime

import pycldf.dataset
from clldutils.path import Path
from pycldf.sources import Source

def swap(dictionary):
    """Turn a key:value dict into a value:{keys} dict.

    All values in `dictionary` must be hashable.

    >>> swap({1: 2, 2: 2, 3: 4})
    {2: {1, 2}, 4: {3}}
    """
    swapped = {}
    for key, value in dictionary.items():
        swapped.setdefault(value, set()).add(key)
    return swapped


if __name__ == "__main__":
    parser = ArgumentParser(
        description=__doc__.split("\n")[0] + """

        The CLDF dataset must have a separate CognateTable. Updates will be
        appended to that table, existing data will not be touched.

        The Edictor file has to be a TSV file with an ID column compatible to
        the dataset's Form_ID, and cognate classes stored in the `cogid` and
        alignments stored in the ALIGNMENT column.""")
    parser.add_argument(
        "edictor", nargs="?", type=FileType("r"),
        help="Edictor file to use as data source")
    parser.add_argument(
        "cldf", nargs="?", type=Path, default=Path("Wordlist-metadata.json"),
        help="CLDF metadata file for the dataset to be updated")
    parser.add_argument(
        "--source-id", default="edictor",
        help="""The ID of the source to assign to the updates. If the ID does not exist in
        the dataset's bibliograpy, it will be created as new @misc entry.""")
    parser.add_argument(
        "--cogid", default="COGID",
        help="""Name of the column containing the cognate set ids""")
    args = parser.parse_args()

    # Check CLDF argument, in order to fail early if this fails.
    dataset = pycldf.dataset.Wordlist.from_metadata(args.cldf)

    # Read new cognate classes and their alignments
    new_cognateset_assignments = {}
    alignments = {}
    for row in csv.DictReader(
            args.edictor, delimiter="\t"):
        if not any(row.values()):
            # LingPy has comment rows
            continue
        new_cognateset_assignments[row["REFERENCE"]] = row[args.cogid]
        try:
            alignments[row["REFERENCE"]] = row["ALIGNMENT"].split()
        except AttributeError:
            print(row)
            raise
    new_cognatesets = swap(new_cognateset_assignments)

    # Column names are assumed to follow standard CLDF CognateTable conventions.
    original_rows = []
    data_on_form = {}
    official_cognateset_assignments = {}
    for r, row in enumerate(dataset["CognateTable"].iterdicts()):
        original_rows.append(row)
        data_on_form[row["Form_ID"]] = row
        official_cognateset_assignments[row["Form_ID"]] = row["Cognateset_ID"]
        try:
            max_row_id = max(max_row_id, row["ID"])
        except NameError:
            max_row_id = row["ID"]
    official_cognatesets = swap(official_cognateset_assignments)

    # Find changed alignments
    for form, data in data_on_form.items():
        if data.get(form, {"Alignment": None})["Alignment"] == alignments.get("form", False):
            del alignments[form]

    # Construct a set of minimal changes to update cognate sets
    pairs, overlaps = [], []

    # First, sort all pairs of old and new cognate sets by overlap.
    still_to_match = new_cognatesets.copy()
    for name, cognateset in list(official_cognatesets.items()):
        cognateset = cognateset.copy()
        for new_name, new_cognateset in list(still_to_match.items()):
            if cognateset == new_cognateset:
                # This cognate set has not changed, ignore.
                continue

            overlap = cognateset & new_cognateset
            if not overlap:
                # There is no overlap.
                continue

            # This cognate set has changed.
            official_cognatesets.pop(name, None)

            # Insert the pair into an ordered table of pair sizes. Ensure
            # biggest overlaps come first.
            index = bisect.bisect(overlaps, -len(overlap))
            overlaps.insert(index, -len(overlap))
            pairs.insert(index, (name, new_name))

            remainder = new_cognateset - overlap
            if remainder:
                still_to_match[new_name] = remainder
            else:
                # All entries of this set have been accounted for, remove it.
                del still_to_match[new_name]

            cognateset -= overlap
            if not cognateset:
                # All entries of this set have been accounted for, no need to look further.
                break

    # Now greedily assign new cognate class ids based on the old ones. (This
    # greedy algorithm is not optimal, but that issue should not be too
    # relevant.)
    other_seen = set()
    moved_forms = {}
    for name, other in pairs:
        if other in other_seen:
            continue
        else:
            new_name = name
            while new_name in official_cognatesets:
                new_name = new_name + "X"
            for form in new_cognatesets[other]:
                if official_cognateset_assignments[form] != new_name:
                    moved_forms[form] = new_name
            other_seen.add(other)


    def new_rows(defaults, last_row_id, moved_forms, realigned_forms, source):
        t = type(last_row_id)
        i = 0
        for i, (form_id, new_cognateset) in enumerate(moved_forms.items()):
            row = defaults[form_id].copy()
            row["ID"] = last_row_id + t(i+1)
            row["Cognateset_ID"] = new_cognateset
            row["Source"] = [source.id]
            if form_id in realigned_forms:
                row["Alignment"] = realigned_forms[form_id]
                row["Alignment_source"] = [source.id]
            print(row)
            yield row
        for j, (form_id, new_alignment) in enumerate(realigned_forms.items()):
            row["ID"] = last_row_id + t(i+j+1)
            row = defaults[form_id].copy()
            row["Alignment"] = realigned_forms[form_id]
            row["Source"] = defaults["Source"] + [source.id]
            print(row)
            yield row

    try:
        source = dataset.sources[args.source_id]
    except ValueError:
        source = Source('misc', id_=args.source_id, year=datetime.date.today().year)
        dataset.sources.add(source)

    dataset["CognateTable"].write(itertools.chain(original_rows, new_rows(
        data_on_form,
        max_row_id,
        moved_forms,
        alignments,
        source)))
    dataset.write_sources()
