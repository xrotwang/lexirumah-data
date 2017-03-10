#!/usr/bin/env python

"""Transform word list data into an input file for edictor.

Rename columns of all_data.tsv to the ones expected by edictor.
Optionally, also use lingpy for automated cognate coding and
alignment.

"""

import sys

import pandas
import argparse
import pyclpa.util
from lingpy import LexStat, Alignments


def cognate_detect(segments):
    """Perform automatic cognate detection.

    Based on the phoneme segmentation described by `segments`, cluster
    the forms into cognate classes.

    """
    ...


def cldf_to_lingpy(data, replacement={
        'Feature_ID': 'CONCEPT_ID',
        'Language_ID': 'DOCULECT_ID',
        'Cognate Set': 'COGNATE_SET',
        'English': 'CONCEPT',
        'Language name (-dialect)': 'DOCULECT',
        'Value': 'IPA'}):
    """Turn CLDF column headers into LingPy column headers."""
    cols = [replacement.get(c, c.upper()) for c in data.columns]
    data.columns = cols


def alignment(data):
    """Generate alignment-like entries from a sequence of forms.

    Take the columns IPA (of forms) and ALIGNMENT (of
    space-separated components of alignments – IPA symbols, markers or
    gaps) and generate ALIGNMENT where it does not make sense.

    """
    for form, alignment in data[["IPA", "ALIGNMENT"]].values:
        form = str(form).replace("\n", ";").replace(" ", "_")
        alignment = alignment.replace("\n", ";")
        if alignment in ("", "nan"):
            yield " ".join(tokenize(form))
        else:
            if list(tokenize(form)) != [
                    x
                    for x in alignment.split()
                    if x != "-"]:
                yield " ".join(tokenize(form))
            else:
                yield alignment


def tokenize(form,
             whitelist=pyclpa.util.load_whitelist(),
             clpadata=pyclpa.util.load_CLPA(),
             substitutions={
                "ä": "a",
                "ε": "ɛ",
                "é": "e",
                "á": "a",
                "í": "i",
                "Ɂ": "ʔ",
                "ˈ": "'",
                ":": "ː",
                "ɡ": "g"}):
    """Tokenize an IPA form according to CLPA.

    Split the form into segments, each ending with a CLPA vowel or
    consonant.

    """
    if form[0] == "*":
        form = form[1:]

    consonants = [clpadata[c]["glyph"] for c in clpadata["consonants"]]
    vowels = [clpadata[c]["glyph"] for c in clpadata["vowels"]]
    segment = ""
    stress = False
    for symbol in form:
        if symbol in substitutions:
            symbol = substitutions[symbol]
        if symbol in ["'"]:
            if segment:
                yield segment
            stress = True
            segment = ""
        elif symbol in ["_", "-"]:
            if segment:
                yield segment
            yield symbol
            segment = ""
        elif symbol in ["."]:
            if segment:
                yield segment
            segment = ""
        elif symbol in consonants:
            if segment:
                yield segment
            segment = symbol
            stress = False
        elif symbol in vowels:
            if segment:
                yield segment
            if stress:
                segment = "'" + symbol
            else:
                segment = symbol
        else:
            segment += symbol
    yield segment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("filename", default="all_data.tsv", nargs="?",
                        help="Input filename containing word lists")
    parser.add_argument("--keep-orthographic", default=False, action='store_true',
                        help="Do not remove orthographic variants")
    parser.add_argument("--within-meaning", default=False, action='store_true',
                        help="Split cross-semantic cognate classes at meaning boundaries")
    parser.add_argument("--start", type=int, default=0,
                        help="Start running at step START")
    args = parser.parse_args()

    if args.start <= 0:
        data = pandas.io.parsers.read_csv(
            args.filename,
            sep="," if args.filename.endswith(".csv") else "\t",
            na_values=[""],
            keep_default_na=False,
            encoding='utf-8')

        if not args.keep_orthographic:
            data = data[~data["Language_ID"].str.endswith("-o")]

        cldf_to_lingpy(data)



        data = data[~pandas.isnull(data["IPA"])]

        data["IPA"] = [x.replace(" ", "_") for x in data["IPA"]]
        data["TOKENS"] = [" ".join(tokenize(x)) for x in data["IPA"]]

        data["ALIGNMENT"] = list(alignment(data))

        data["COGNATE_SET"] = [
            "" if (i=='nan' or pandas.isnull(i) or not i) else
            list(set(data["COGNATE_SET"])).index(i)
            for i in data["COGNATE_SET"]]

        data["COMMENT"] = [
            x.replace("\n", "; ")
            for x in data["COMMENT"]]

        data.to_csv(
            "unaligned.tsv",
            sep='\t',
            index_label="ID",
            na_rep="",
            encoding='utf-8')

    if args.start <= 1:
        lex = LexStat("unaligned.tsv")
        lex.get_scorer(preprocessing=False,
                       runs=10000, ratio=(2, 1), vscale=1.0)
        lex.cluster(cluster_method='upgma',
                    method='lexstat',
                    ref='auto_cogid',
                    threshold=0.8)
        lex.output("tsv", filename="tap-cognates", ignore="all",
                   prettify=False)
        scorer = lex.bscorer

    if args.start <= 2:
        cognates = pandas.read_csv(
            'tap-cognates.tsv', sep='\t', keep_default_na=False,
            na_values=[""])

        cognates = cognates[~(
            pandas.isnull(cognates["DOCULECT"])
            | pandas.isnull(cognates["CONCEPT_ID"]))]

        cognates.sort_values(by="DOCULECT", inplace=True)

        cognates["LONG_COGID"] = None
        for i, row in list(cognates.iterrows()):
            cognateset = row["COGNATE_SET"]
            if cognateset == "nan" or not cognateset or pandas.isnull(
                    cognateset):
                cogid = row["AUTO_COGID"]
                representatives = cognates[cognates["AUTO_COGID"] == cogid]
                representative = representatives.iloc[0]
                cognates.set_value(i, "LONG_COGID",
                                   representative["COGNATE_SET"])
            else:
                cognates.set_value(i, "LONG_COGID", row["COGNATE_SET"])

        short = {"Austronesian": "AN",
                "Timor-Alor-Pantar": "TAP"}
        cognates["DOCULECT"] = [
            "{:s} – {:s} {:s}".format(
                "X" if pandas.isnull(region) else region,
                "X" if pandas.isnull(family) else short.get(family, family),
                "X" if pandas.isnull(lect) else lect)
            for lect, family, region in zip(
                    cognates["DOCULECT"], cognates["FAMILY"], cognates["REGION"])]

        COG_IDs = []
        if args.within_meaning:
            for _, i in cognates[["LONG_COGID", "CONCEPT_ID"]].iterrows():
                i = tuple(i)
                if i not in COG_IDs:
                    COG_IDs.append(i)
            cognates["COGID"] = [
                COG_IDs.index(tuple(x))
                for _, x in cognates[["LONG_COGID", "CONCEPT_ID"]].iterrows()]
        else:
            for i in cognates["LONG_COGID"]:
                if i not in COG_IDs:
                    COG_IDs.append(i)
            cognates["COGID"] = [
                COG_IDs.index(x)
                for x in cognates["LONG_COGID"]]
        cognates.to_csv("tap-cognates-merged.tsv",
                        index=False,
                        na_rep="",
                        sep="\t")

    if args.start <= 3:
        sys.exit()

        # align data
        alm = Alignments('tap-cognates-merged.tsv', ref='COGID',
                         segments='ALIGNMENT', transcription='IPA',
                         alignment='ALIGNMENT')
        alm.align(override=True, alignment='AUTO_ALIGNMENT', iteration=True,
                  mode="dialign", method="progressive", model="sca")
        alm.output('tsv', filename='tap-aligned', ignore='all', prettify=False)

    if args.start <= 4:
        alignments = pandas.read_csv(
            'tap-aligned.tsv',
            sep="\t",
            na_values=[""],
            keep_default_na=False,
            encoding='utf-8')
        for cogid, cognate_class in alignments.groupby("COGID"):
            is_aligned = {None
                        if pandas.isnull(x)
                        else len(x.split())
                        for x in cognate_class['ALIGNMENT']}
            if len(is_aligned) != 1:
                # Alignment lengths don't match, don't trust the alignment
                for i in cognate_class.index:
                    alignments.set_value(i, 'ALIGNMENT',
                                        alignments.loc[i].get('AUTO_ALIGNMENT', '-'))

        alignments.to_csv("tap-alignments-merged.tsv",
                        index=False,
                        na_rep="",
                        sep="\t")
