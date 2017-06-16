#!/usr/bin/env python

"""Similarity code tentative cognates in a word list"""

import pandas
import pickle

import sys
import argparse

import infomapcog.clustering as clust

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=sys.stdin, nargs="?",
                        type=argparse.FileType('r'),
                        help="Input file containing word list")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write segmented data to")
    parser.add_argument("--lodict", default=None,
                        type=argparse.FileType('rb'),
                        help="Phonetic segment similiarity dictionary")
    parser.add_argument(
        "--tokens", default="Tokens",
        help="Column name with tokenized (space-separated) values for coding")
    parser.add_argument("--asjp", action="store_const", const="ASJP",
                        dest="tokens",
                        help="Use ASJP classes for similarity coding")
    args = parser.parse_args()

    if args.lodict is None:
        lodict = {}
    else:
        lodict = pickle.load(args.lodict)

    data = pandas.io.parsers.read_csv(
        args.input,
        sep="\t",
        na_values=[""],
        keep_default_na=False,
        encoding='utf-8')

    words_dict = {
        concept: {
            language: [
                tuple(tokens.split()) for tokens in blob[args.tokens]]
            for language, blob in by_concept.groupby("Language_ID")}
        for concept, by_concept in data.groupby("English")}

    codes = clust.cognate_code_infomap2(
        words_dict, lodict,
        gop=-2.5, gep=-1.75, threshold=0.001, method='infomap')

    lex = data.set_index(["English", "Language_ID", args.tokens])
    lex["Similarity Set"] = None
    for i, similarityset in enumerate(codes):
        similarityset = sorted(similarityset)
        c0, l0, w0 = similarityset[0]
        representative = (c0, l0, ''.join(w0))
        for c, l, w in similarityset:
            lex.set_value((c, l, ' '.join(w)),
                          "Similarity Set",
                          str(representative))

    lex.to_csv(
        args.output,
        index=True,
        sep='\t',
        na_rep="",
        encoding='utf-8')
