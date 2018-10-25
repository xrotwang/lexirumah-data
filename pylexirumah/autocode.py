#!/usr/bin/env python

"""Similarity code tentative cognates in a word list and align them"""

import sys
from pycldf.util import Path
import argparse

import lingpy
import lingpy.compare.partial

from pylexirumah import get_dataset

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
        if not segments[s - 1]:
            del segments[s - 1]
            continue
        if segments[s - 1] == "0":
            del segments[s - 1]
            continue
        if segments[s - 1] in "_#◦+→←" and segments[s] in "_#◦+→←":
            del segments[s - 1]
            continue
    row["Segments"] = segments[1:-1]
    return row["Segments"]


def clean_segments_and_rename(new_column_names):
    def filter(row):
        result = clean_segments(row)
        for old, new in new_column_names.items():
            row[new] = row.pop(old)
        return result
    return filter


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=Path("Wordlist-metadata.json"),
                        nargs="?", type=Path,
                        help="Input file containing the CLDF word list."
                        " (default: ./Wordlist-metadata.json")
    parser.add_argument("output", nargs="?",
                        # type=argparse.FileType('w'),
                        default="aligned",
                        help="Output file to write segmented data to")
    parser.add_argument("--threshold", default=0.55,
                        type=float,
                        help="Cognate clustering threshold value. (default:"
                        " 0.55)")
    parser.add_argument("--cluster-method", default="infomap",
                        help="Cognate clustering method name. Valid options"
                        " are, dependent on your LingPy version, {'upgma',"
                        " 'single', 'complete', 'mcl', 'infomap'}."
                        " (default: infomap)")
    args = parser.parse_args()

    dataset = get_dataset(args.input)

    # Explicit is better than implicit, so from_cldf does not contain renaming
    # functionality, but it does contain a callback hook that can modify each
    # row an filter it.
    rename_columns = {
         dataset["FormTable", "parameterReference"].name: "concept",
         dataset["FormTable", "languageReference"].name: "doculect",
         dataset["FormTable", "segments"].name: "tokens",
         dataset["FormTable", "form"].name: "ipa",
         dataset["FormTable", "id"].name: "reference",
    }

    lex = lingpy.compare.partial.Partial.from_cldf(
        args.input, filter=clean_segments_and_rename(rename_columns))

    try:
        scorers_etc = lingpy.compare.lexstat.LexStat("lexstats.tsv")
        lex.scorer = scorers_etc.scorer
        lex.cscorer = scorers_etc.cscorer
        lex.bscorer = scorers_etc.bscorer
    except (OSError, ValueError):
        lex.get_scorer(runs=10000)
        lex.output('tsv', filename='lexstats', ignore=[])
    # For some purposes it is useful to have monolithic cognate classes.
    lex.cluster(method='lexstat', threshold=args.threshold, ref='cogid',
                cluster_method=args.cluster_method, verbose=True)
    # But actually, in most cases partial cognates are much more useful.
    lex.partial_cluster(method='lexstat', threshold=args.threshold,
                        cluster_method=args.cluster_method, ref='partialids',
                        verbose=True)
    lex.output("tsv", filename="auto-clusters")
    alm = lingpy.Alignments(lex, ref="partialids", fuzzy=True)
    alm.align(method='progressive')
    alm.output('tsv', filename=args.output, ignore='all', prettify=False)
