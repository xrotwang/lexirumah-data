#!/usr/bin/env python

"""Segment all IPA strings in a word list."""

import pandas

import sys
import argparse

from lingpy import ipa2tokens
import pyclpa.base


CLPA = pyclpa.base.CLPA()


WHITELIST = {
    " ": "_",
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
        for before, after in WHITELIST.items():
            ipa = ipa.replace(before, after)
    tokenized_word = ipa2tokens(
        ipa, merge_vowels=False, merge_geminates=False)
    token = 0
    index = 0
    # For each character in the original IPA string, check the corresponding
    # character in the newly created list of tokens.
    for i in ipa:
        try:
            tokenized_word[token][index]
        except IndexError:
            token += 1
            index = 0
        try:
            # If the characters do not match...
            # TODO: Finish comments
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


def tokenize_and_enforce_clpa(form, ignore_clpa_errors=True, additional={}):
    """Return the CLPA sequence of a word form.

    If ignore_clpa_errors, return the sequence even if it contains unknown segments;
    otherwise (ignore_clpa_errors==False), raise an exception for invalid CLPA.

    >>> " ".join([str(x) for x in  tokenize_and_enforce_clpa("baa")])
    'b aː'

    >>> " ".join([str(x) for x in  tokenize_and_enforce_clpa("a9b", ignore_clpa_errors=False)])
    Traceback (most recent call last):
      ...
    ValueError: "9" is not a valid CLPA segment.

    """
    result = []
    index_fw = 0
    index_bw = len(form)
    while True:
        if index_bw == index_fw:
            return result
        possible_token = CLPA(form[index_fw:index_bw], additional)[0]
        if isinstance(possible_token, pyclpa.base.Sound):
            result.append(possible_token)
            index_fw = index_bw
            index_bw = len(form)
        else:
            index_bw -= 1


    # TODO: Finish the definition of this function.
    # Make sure that the expected error in the doctest points to the appropriate segment


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

    # Tokenize IPA, also to ASJP
    data["Tokens"] = [" ".join(tokenize_word_reversibly(x, clean=True))
                      for x in data["Value"]]

    from infomapcog.ipa2asjp import ipa2asjp

    data["ASJP"] = [" ".join(ipa2asjp(x))
                    for x in data["Value"]]

    # Clean up NaN values in cognate sets
    data["Cognate Set"] = [
        float("nan") if (i == 'nan' or pandas.isnull(i) or not i) else i
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
