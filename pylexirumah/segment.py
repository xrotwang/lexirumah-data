#!/usr/bin/env python

"""Segment all IPA strings in a word list."""

import pandas

import sys
import argparse

from lingpy import ipa2tokens

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


def tokenize_word_reversibly(ipa, clean=False):
    """Reversibly convert an IPA string into a list of tokens.

    In contrast to LingPy's tokenize_word, do this without removing
    symbols. This means that the original IPA string can be recovered
    from the tokens.

    >>> tokenize_word_reversibly("kə'tːi  'lɔlɔŋ")
    ["k", "ə", "'tː", "i", "  ", "'l", "ɔ", "l", "ɔ", "ŋ"]

    """
    if clean:
        for before, after in clean.items():
            ipa = ipa.replace(before, after)
    tokenized_word = ipa2tokens(
        ipa, merge_vowels=False, merge_geminates=False)
    token = 0
    index = 0
    for i in ipa:
        try:
            tokenized_word[token][index]
        except IndexError:
            token += 1
            index = 0
        try:
            if i != tokenized_word[token][index]:
                if index == 0:
                    tokenized_word.insert(token, i)
                else:
                    tokenized_word[token] = (
                        tokenized_word[token][:index] +
                        i +
                        tokenized_word[token][index:])
        except IndexError:
            tokenized_word.append(i)
        index += 1
    # assert ''.join(tokenized_word) == ipa
    return tokenized_word


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

    data = pandas.read_csv(
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

    from infomapcog.ipa2asjp import ipa2asjp

    data["ASJP"] = [" ".join(ipa2asjp(x))
                    for x in data["IPA"]]

    # Clean up NaN values in cognate sets
    data["Cognate Set"] = [
        float("nan") if (i == 'nan' or pandas.isnull(i) or bool(i) == False) else i
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
