#!/usr/bin/env python

"""Merge different cognate coding files"""

import pandas

import sys
import argparse

from infomapcog.ipa2asjp import ipa2asjp, tokenize_word_reversibly

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=sys.stdin,
                        type=argparse.FileType('r'),
                        help="Input filename containing word list")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write merged data to")
    parser.add_argument("--other", default=None,
                        type=argparse.FileType('r'),
                        help="Other word list containing alternative codings")
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

    # Read the original data file
    data = pandas.io.parsers.read_csv(
        args.input,
        sep="\t",
        na_values=[""],
        index_col=["English", "Language_ID", "Value"],
        keep_default_na=False,
        encoding='utf-8')
    data.sort_index(inplace=True)

    # If cognate classes from a different file should be merged in,
    # read that. (Otherwise, do practically nothing.)
    if args.other:
        other = pandas.io.parsers.read_csv(
            args.other,
            sep="\t",
            na_values=[""],
            index_col=["English", "Language_ID", "Value"],
            keep_default_na=False,
            encoding='utf-8')
        other.sort_index(inplace=True)
    else:
        other = data

    # Parse the `reset` switch.
    reset_these = [r.split("=")
                   for r in args.reset
                   if r.count("=") == 1]

    # Prepare the output column
    if args.output_col in [args.input_col, args.other_col]:
        raise ValueError("Output column may not be also an input column.")
    data[args.output_col] = None

    for (c, l, v), row in list(data.iterrows()):
        # The cognateset is reset if it's not defined, or if a request
        # was explicitly requested.
        cognateset = row[args.input_col]
        reset = cognateset == "nan" or not cognateset or pandas.isnull(
                cognateset)
        for col, const in reset_these:
            if col == "English":
                reset |= c == const
            elif col == "Language_ID":
                reset |= l == const
            elif col == "Value":
                reset |= v == const
            else:
                reset |= row[col] == const

        try:
            # Find the first row in that cognateset and use its index
            # (C,L,V) as a representative of the class.
            representatives = data[data[args.input_col] == cognateset]
            representative = representatives.index[0]
        except IndexError:
            representative = None

        if reset or representative is None:
            # Find the first row in the *other* file that shares the
            # *other* cognate class with this word. Assuming sorted
            # indices, that would be this word or a word we have
            # already handled, so that word should have a reasonable
            # representative set.
            try:
                other_rows_for_this_form = other.loc[(c, l, v)]
                other_cogid = other_rows_for_this_form.iloc[0][args.other_col]
                other_representatives = other[
                    other[args.other_col] == other_cogid]
                representative = other_representatives.index[0]
                assert representative <= (c, l, v)
            except IndexError:
                representative = None

        data.set_value((c, l, v), args.output_col, str(representative))

    data.to_csv(args.output,
                index=True,
                na_rep="",
                sep="\t")
