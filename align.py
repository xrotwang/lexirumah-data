#!/usr/bin/env python

"""Automatically align similar forms"""

import copy

import newick
import pandas
import pickle

import sys
import argparse

import infomapcog.dataio as dataio

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
    parser.add_argument("--cognate-col", default="Group",
                        help="Column containing the cognate classes")
    parser.add_argument("--guide-tree", type=argparse.FileType('r'),
                        help="Newick tree to use as guide tree for multi-alignment")
    parser.add_argument("--only-necessary", action='store_true', default=False,
                        help="Only align those classes that appear unaligned")
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
        encoding='utf-8',
        index_col=["English", "Language_ID", "IPA"])

    if args.guide_tree:
        tree = newick.load(args.guide_tree)[0]
    else:
        raise argparse.ArgumentError
        # Calculate an UPGMA tree or something
        
    for i, cognateclass in data.groupby(args.cognate_col):
        if args.only_necessary and len(set([
                len(r.split()) for r in cognateclass["Alignment"]])) == 1:
            continue
        as_dict = [
            {(c, l, tuple(row[args.tokens].split()))
                for (c, l, t), row in cognateclass.iterrows()}]
        for group, (languages, concepts, algs) in dataio.multi_align(
                as_dict, copy.deepcopy(tree),
                lodict=dataio.MaxPairDict(lodict),
                gop=-2.5, gep=-1.75).items():
            for language, concept, alg in zip(
                    languages, concepts, zip(*algs)):
                print(alg)
                try:
                    data.set_value(
                        (language, concept, ''.join(alg)),
                        "Alignment",
                        " ".join([a or '-' for a in alg]))
                except Exception:
                    import pdb
                    pdb.set_trace()
                    raise

    data.to_csv(args.output,
                index=True,
                na_rep="",
                sep="\t")
