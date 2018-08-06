#!/usr/bin/env python

"""Similarity code tentative cognates in a word list and align them"""

import sys
from pycldf.util import Path
import argparse

import lingpy


def clean_segments(row):
    row["Segments"] = [x for x in row["Segments"] if x]
    return row["Segments"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=Path("Wordlist-metadata.json"), nargs="?",
                        type=Path,
                        help="Input file containing the CLDF word list. (default: ./Wordlist-metadata.json")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write segmented data to")
    parser.add_argument("--lodict", default=None,
                        type=argparse.FileType('rb'),
                        help="Phonetic segment similiarity dictionary")
    parser.add_argument("--asjp", action="store_const", const="ASJP",
                        dest="tokens",
                        help="Use ASJP classes for similarity coding")
    args = parser.parse_args()

    lex = lingpy.LexStat.from_cldf(
        args.input,
        col="lect_id", row="concept_id", segments="segments", transcription="form",
        filter=clean_segments)
    lex.get_scorer(runs=1000)
    lex.output('tsv', filename='lexstats', ignore=[])
    lex.cluster(method='lexstat', threshold=0.55, ref='cogid-infomap', cluster_method="infomap", verbose=True)
    lex.output("tsv", filename="auto-clusters")
    alm = lingpy.Alignments(lex,
        col="lect_id", row="concept_id", segments="segments", transcription="form",
        ref="cogid-infomap")
    alm.align(method='progressive', scoredict=lex.cscorer)
    alm.output('tsv', filename='aligned', ignore='all', prettify=False)
