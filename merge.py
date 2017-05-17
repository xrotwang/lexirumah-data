#!/usr/bin/env python

"""Segment all IPA strings in a word list."""

import pandas

import sys
import argparse

from infomapcog.ipa2asjp import ipa2asjp, tokenize_word_reversibly

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=sys.stdin,
                        type=argparse.FileType('r'),
                        help="Input filename containing word list")
    parser.add_argument("--other", default=None,
                        type=argparse.FileType('r'),
                        help="Other word list containing alternative codings")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write merged data to")
    parser.add_argument("--input-col", default="Cognate Set",
                        help="Column containing classes in the input")
    parser.add_argument("--other-col", default="Similarity Set",
                        help="Column containing classes in the other")
    parser.add_argument("--output-col", default="Group",
                        help="Column to write merged classes to")
    parser.add_argument("--reset", action="append", default=[],
                        help="'column=value' sets to reset to automatic coding")
    parser.add_argument("--log", action="store_true", default=False,
                        help="Show which classes are moved")
    args = parser.parse_args()

    data = pandas.io.parsers.read_csv(
        args.input,
        sep="\t",
        na_values=[""],
        index_col=["English", "Language_ID", "IPA"],
        keep_default_na=False,
        encoding='utf-8')

    if args.other:
        other = pandas.io.parsers.read_csv(
            args.other,
            sep="\t",
            na_values=[""],
            index_col=["English", "Language_ID", "IPA"],
            keep_default_na=False,
            encoding='utf-8')
    else:
        other = data

    reset_these = [r.split("=")
                   for r in args.reset
                   if r.count("=") == 1]

    if args.output_col in [args.input_col, args.other_col]:
        print("If the output column is identical to an input column, behaviour is not well-defined. Continuing anyway.",
              file=sys.stderr)
    data[args.output_col] = None

    for (c, l, v), row in list(data.iterrows()):
        cognateset = row[args.input_col]
        reset = cognateset == "nan" or not cognateset or pandas.isnull(
                cognateset)
        for col, const in reset_these:
            if col == "English":
                reset |= c == const
            elif col == "Language_ID":
                reset |= l == const
            elif col == "IPA":
                reset |= v == const
            else:
                reset |= row[col] == const

        try:
            cogid = row[args.input_col]
            representatives = data[data[args.input_col] == cogid]
            representative = representatives.index[0]
        except IndexError:
            representative = None

        try:
            other_rows = other.loc[(c, l, v)]
            other_cogid = other_rows.iloc[0][args.other_col]
            other_representatives = other[
                other[args.other_col] == other_cogid]
            other_representative = other_representatives.index[0]
        except IndexError:
            other_representative = None

        if reset:
            representative = other_representative
        elif args.log:
            if (representative != other_representative or not representative):
                print((c, l, v), ":", representative, "→", other_representative)
        data.set_value((c, l, v), args.output_col, str(representative))

    data.to_csv(args.output,
                index=True,
                na_rep="",
                sep="\t")
