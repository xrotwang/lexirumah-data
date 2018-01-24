#!/usr/bin/env python3

"""Update cognate codes and alignments of a CLDF dataset from an Edictor file.

Example
-------
    $ python pylexirumah/append_changed_cognate_classes.py edictor.tsv
"""

import bisect
import itertools
import collections

from argparse import ArgumentParser, FileType

import csv
import datetime

import pycldf.dataset
from clldutils.path import Path
from pycldf.sources import Source


def swap(dictionary):
    """Turn a key:value dict into a value:{keys} dict.

    All values in `dictionary` must be hashable.

    Parameters
    ----------
    dictionary : dict

    Returns
    -------
    dict
        Dictionary where the keys and values are swapped with respect to the
        passed dictionary. If a previous value is found under multiple previous keys,
        these keys are now grouped as a value tuple under the new key.

    Examples
    --------
    >>> swap({1: 2, 2: 2, 3: 4})
    {2: {1, 2}, 4: {3}}
    """
    swapped = {}
    for key, value in dictionary.items():
        swapped.setdefault(value, set()).add(key)
    return swapped


def main(args):
    """ Update cognate codes and alignments of a CLDF dataset from an Edictor file.

    Parameters
    ----------
    args : Namespace
        A Namespace object with several properties listed below.
        edictor : FileType
            ...
        cldf : Path, optional
            Path to the CLDF metadata json file.
        source-id : str, optional
            String used to source any changes to cognate codes or alignments. This defaults
            to "edictor".
        cogid : str, optional
            String that specifies the header of the column containing the cognate
            set id's in the Edictor file. This defaults to "COGID".

    Notes
    -----
        Once this function is called with the proper arguments, cognates.csv in the CLDF
        dataset is updated based on the output of Edictor when changes are made to
        cognate codes or alignments.
        Sources.bib also gets updated with a new source if specified.
    """
    # Check CLDF argument, in order to fail early if this fails.
    dataset = pycldf.dataset.Wordlist.from_metadata(args.cldf)

    # Read new cognate classes and their alignments
    new_cognateset_assignments = {}
    alignments = {}
    for row in csv.DictReader(
            args.edictor, delimiter="\t"):
        if row["ID"].startswith("#") or not row["ID"] or not row["REFERENCE"]:
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
        if data.get("Alignment", None) == alignments.get(form, False):
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
            # biggest overlaps come first, so actually work with their negatives.
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
    moved_forms = collections.OrderedDict()
    for index, (name, other) in enumerate(pairs):
        if other in other_seen:
            continue
        else:
            new_name = name
            while new_name in official_cognatesets:
                new_name = new_name + "X"
            official_cognatesets[new_name] = set()
            for form in new_cognatesets[other]:
                if official_cognateset_assignments.get(form) != new_name:
                    moved_forms[form] = new_name
                official_cognatesets[new_name].add(form)
            other_seen.add(other)

    try:
        source = dataset.sources[args.source_id]
    except ValueError:
        source = Source('misc', id_=args.source_id, year=str(datetime.date.today().year))
        dataset.sources.add(source)
        dataset.write_sources()

    def new_rows(defaults, last_row_id, moved_forms_p, realigned_forms, source_p):
        # TODO: Make a docstring?
        # What is the benefit of defining this within the main function?
        t = type(last_row_id)
        i = 0   # FIXME: Is this assignment necessary?
        empty = {"Alignment": [], "Source": []}
        for i, (form_id, new_cognateset_it) in enumerate(moved_forms_p.items()):
            row_new = defaults.get(form_id, empty).copy()
            row_new["ID"] = last_row_id + t(i+1)
            row_new["Form_ID"] = form_id
            row_new["Cognateset_ID"] = new_cognateset_it
            if form_id in realigned_forms:
                row_new["Alignment"] = realigned_forms[form_id]
                row_new["Source"] = [source.id]
            else:
                row_new["Alignment"] = defaults[form_id]["Alignment"]
                row_new["Source"] = defaults[form_id]["Source"] + [source_p.id]
            print(row_new)
            yield row_new
        for j, (form_id, new_alignment) in enumerate(realigned_forms.items()):
            if not new_alignment:
                continue
            row_new = defaults.get(form_id, empty).copy()
            row_new["ID"] = last_row_id + t(i+j+2)
            row_new["Alignment"] = realigned_forms[form_id]
            row_new["Source"].append(source.id)
            print(row_new)
            yield row_new

    dataset["CognateTable"].write(itertools.chain(original_rows, new_rows(
        data_on_form,
        max_row_id,
        moved_forms,
        alignments,
        source)))


if __name__ == "__main__":
    parser = ArgumentParser(
        description=__doc__.split("\n")[0] + """

        The CLDF dataset must have a separate CognateTable. Updates will be
        appended to that table, existing data will not be touched.

        The Edictor file has to be a TSV file with an ID column compatible to
        the dataset's Form_ID, and cognate classes stored in the `cogid` and
        alignments stored in the ALIGNMENT column.""")
    parser.add_argument(
        "edictor", type=FileType("r"),
        help="Edictor file to use as data source")
    parser.add_argument(
        "cldf", nargs="?", type=Path, default=Path("cldf/Wordlist-metadata.json"),
        help="CLDF metadata file for the dataset to be updated")
    parser.add_argument(
        "--source-id", default="edictor",
        help="""The ID of the source to assign to the updates. If the ID does not exist in
        the dataset's bibliograpy, it will be created as new @misc entry.""")
    parser.add_argument(
        "--cogid", default="COGID",
        help="""Name of the column containing the cognate set ids""")
    arguments = parser.parse_args()

    main(arguments)
