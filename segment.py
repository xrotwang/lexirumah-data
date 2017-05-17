#!/usr/bin/env python

"""Segment all IPA strings in a word list."""

import pandas

import sys
import argparse

from infomapcog.ipa2asjp import ipa2asjp, tokenize_word_reversibly

clean = {" ": "_",
         "ä": "a",
         "ε": "ɛ",
         "é": "e",
         "á": "a",
         "í": "i",
         "Ɂ": "ʔ",
         "ˈ": "'",
         ":": "ː",
         "ɡ": "g",
         "R": "ʀ",
         'dʒ͡': 'd͡ʒ',
         'ʤ': 'd͡ʒ'}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default="all_data.tsv", nargs="?",
                        type=argparse.FileType('r'),
                        help="Input filename containing word list")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write segmented data to")
    parser.add_argument("--keep-orthographic", default=False, action='store_true',
                        help="Do not remove orthographic variants")
    args = parser.parse_args()

    data = pandas.io.parsers.read_csv(
        args.input,
        sep="\t",
        na_values=[""],
        keep_default_na=False,
        encoding='utf-8')

    # Drop orthographic varieties
    if not args.keep_orthographic:
        data = data[~data["Language_ID"].str.endswith("-o")]

    # Drop empty entries
    data = data[~pandas.isnull(data["Value"])]

    # Clean up IPA slightly
    data["IPA"] = data["Value"].str.strip()
    for key, value in clean.items():
        data["IPA"] = data["IPA"].str.replace(key, value)

    # Tokenize IPA, also to ASJP
    data["Tokens"] = [" ".join(tokenize_word_reversibly(x))
                      for x in data["IPA"]]
    data["ASJP"] = [" ".join(ipa2asjp(x))
                    for x in data["IPA"]]

    # Clean up NaN values in cognate sets
    data["Cognate Set"] = [
        float("nan") if (i=='nan' or pandas.isnull(i) or not i) else i
        for i in data["Cognate Set"]]

    # Remove line breaks from comments
    data["Comment"] = [
        x.replace("\n", "; ")
        for x in data["Comment"]]

    data.to_csv(
        args.output,
        index=False,
        sep='\t',
        na_rep="",
        encoding='utf-8')
