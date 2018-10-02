#!/usr/bin/env python

"""Similarity code tentative cognates in a word list and align them"""

import sys
from pycldf.util import Path
import argparse

import lingpy
import lingpy.compare.partial


def clean_segments(row):
    """Reduce the row's segments to not contain empty morphemes.

    This function removes all unknown sound segments (/0/) from the "Segments"
    list of the `row` dict it is passed, and removes empty morphemes by
    collapsing subsequent morpheme boundaries (_#◦+→←) into one. The `row` is
    modified in-place, the resulting cleaned segment list is returned.

    >>> row = {"Segments": list("+_ta+0+at")
    >>> clean_segments(row)
    ['t', 'a', '+', 'a', 't']
    >>> row
    {'Segments': ['t', 'a', '+', 'a', 't']}

    """
    segments = row["Segments"]
    segments.insert(0, "#")
    segments.append("#")
    for s in range(len(segments) - 1, 0, -1):
        if segments[s] == "0":
            del segments[s]
        if segments[s - 1] in "_#◦+→←" and segments[s] in "_#◦+→←":
            del segments[s]
    row["Segments"] = segments[1:-1]
    return row["Segments"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=Path("Wordlist-metadata.json"),
                        nargs="?", type=Path,
                        help="Input file containing the CLDF word list."
                        " (default: ./Wordlist-metadata.json")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write segmented data to")
    args = parser.parse_args()

    lex = lingpy.compare.partial.Partial.from_cldf(
        args.input,
        col="lect_id", row="concept_id", segments="segments", transcription="form",
        filter=clean_segments)
    lex.get_scorer(runs=1000)
    lex.output('tsv', filename='lexstats', ignore=[])
    # For some purposes it is useful to have monolithic cognate classes.
    lex.cluster(method='lexstat', threshold=0.55, ref='cogid', cluster_method="infomap", verbose=True)
    # But actually, in most cases partial cognates are much more useful.
    lex.partial_cluster(method='lexstat', threshold=0.55, ref='partialids', cluster_method="infomap", verbose=True)
    lex.output("tsv", filename="auto-clusters")
    alm = lingpy.Alignments(lex,
        col="lect_id", row="concept_id", segments="segments", transcription="form",
                            ref="partialids", fuzzy=True)
    alm.align(method='progressive')
    alm.output('tsv', filename='aligned', ignore='all', prettify=False)
