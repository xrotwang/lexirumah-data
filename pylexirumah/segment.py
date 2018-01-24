#!/usr/bin/env python

"""Segment all IPA strings in a word list."""

# import pandas

import sys
import argparse

import pyclpa.base


CLPA = pyclpa.base.CLPA()


WHITELIST = {
    # This dictionary is used to convert certain segments from the data
    # to segments that can be recognized by CLPA.
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
    'dʒ͡': 'dʒ',
    'ʤ': 'dʒ'}


def tokenize_clpa(form, ignore_clpa_errors=True, preprocess=WHITELIST):
    """Return the CLPA sequence of a word form.

    If ignore_clpa_errors, return the sequence even if it contains unknown segments;
    otherwise (ignore_clpa_errors==False), raise an exception for invalid CLPA.

    Parameters
    ----------
    form : str
        An IPA string to be tokenized.
    ignore_clpa_errors : bool, optional
        If set to True, segments that are unknown to CLPA will be returned as Unknown
        objects in the list.
        If set to False, whenever a segment cannot be found by CLPA, a ValueError is raised.

        Set to True by default.
    preprocess : dict, optional
        A dictionary that is used to replace sequences in 'form' before processing them with
        this function.

        Set to 'WHITELIST' by default. 'WHITELIST' is defined before this function definition.

    Returns
    -------
    list
        A list of CLPA objects that correspond to the segments in the passed 'form'.

    Raises
    ------
    ValueError
        If 'ignore_clpa_errors' is set to False and
        no corresponding CLPA segment can be found for a segment in 'form'.

        The error message points to that segment.

    Examples
    --------
    >>> " ".join([str(x) for x in tokenize_clpa("baa")])
    'b aː'

    >>> " ".join([str(x) for x in tokenize_clpa("a9b")])
    'a � b'

    >>> " ".join([str(x) for x in tokenize_clpa("a9b", ignore_clpa_errors=False)])
    Traceback (most recent call last):
      ...
    ValueError: "9" is not a valid CLPA segment.
    """
    for before, after in preprocess.items():
        form = form.strip().replace(before, after)

    result = []
    index_fw = 0
    index_bw = len(form)

    while True:
        if index_bw == index_fw and index_bw < len(form):
            # This section dictates what happens when the whole string is not parsed yet and
            # a viable CLPA sequence has not been found.
            if ignore_clpa_errors:
                unknown_segment = CLPA(form[index_bw])[0]
                result.append(unknown_segment)
                index_fw += 1
                index_bw = len(form)
                continue
            else:
                raise ValueError("\"%s\" is not a valid CLPA segment." % (form[index_bw]))
        elif index_fw == len(form):
            return result

        possible_token = CLPA(form[index_fw:index_bw])[0]
        if isinstance(possible_token, pyclpa.base.Sound):
            # This section appends a CLPA match to the list that is to be returned in the end.
            result.append(possible_token)
            index_fw = index_bw
            index_bw = len(form)
        else:
            index_bw -= 1


if __name__ == '__main__':
    def main(args):
        parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
        parser.add_argument("input", default="all_data.tsv", nargs="?",
                            type=argparse.FileType('r'),
                            help="Input filename containing word list")
        parser.add_argument("output", default=sys.stdout, nargs="?",
                            type=argparse.FileType('w'),
                            help="Output file to write segmented data to")
        parser.add_argument("--keep-orthographic", default=False, action='store_true',
                            help="Do not remove orthographic variants")
        args = parser.parse_args(args)

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
