#!/usr/bin/env python

"""Transform word list data into an input file for edictor.

Rename columns of all_data.tsv to the ones expected by edictor.
Optionally, also use lingpy for automated cognate coding and
alignment.

"""

import collections
import copy

import newick
import pandas
import pickle

import sys
import argparse

import pyclpa.util
import lingpy.align.multiple
import infomapcog.clustering as clust
from lingpy import LexStat, Alignments
from infomapcog.ipa2asjp import ipa2asjp, tokenize_word_reversibly
from infomapcog.dataio import multi_align, MaxPairDict

class KeyAwareDefaultDict(collections.defaultdict):
    """A defaultdict that creates based on key."""

    def __missing__(self, key):
        """What to do for a missing key."""
        if self.default_factory is None:
            raise KeyError((key,))
        self[key] = value = self.default_factory(key)
        return value


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


s = {
    'SEGMENT': 0,
    'AUTOCODE': 1,
    'RESET': 2,
    'MERGE': 3,
    'AUTOALIGN': 4,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("filename", default="all_data.tsv", nargs="?",
                        help="Input filename containing word lists")
    parser.add_argument("--keep-orthographic", default=False, action='store_true',
                        help="Do not remove orthographic variants")
    parser.add_argument("--within-meaning", default=False, action='store_true',
                        help="Split cross-semantic cognate classes at meaning boundaries")
    parser.add_argument("--start", type=int, default=0,
                        help="Start running before step START")
    parser.add_argument("--end", type=int, default=3,
                        help="Finish running after step END")
    parser.add_argument("--coding", type=argparse.FileType("r"),
                        help="""Read cognate classes from this file instead of from
                        tap-cognates.tsv – This is useful when you
                        want to re-use an existing automatic cognate
                        coding file: --start 2 --coding unaligned.tsv
                        """)
    parser.add_argument("--scores", type=argparse.FileType("rb"),
                        help="""A file containing a pickled sound similarity dictionary, as
                        eg. generated from PMI scores. Used for
                        alignment and similarity coding. Calculated if
                        not given, which takes time.""")
    parser.add_argument("--align", action='store_true', default=False,
                        help="Re-align all classes")
    parser.add_argument("--reset", action="append", default=[],
                        help="Cognate IDs, meanings and language IDs to reset to automatic coding")
    parser.add_argument(
        "--guide-tree",
        type=argparse.FileType("r"),
        help="""A Newick file containing a single guide tree to combine
        multiple alignments. (Separate guide trees for different families are
        not supported yet.)""")
    args = parser.parse_args()

    if args.start <= 0 <= args.end:
        ...

    if args.start <= s['SEGMENT'] <= args.end:
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

        data["IPA"] = [x.replace(" ", "_").replace("[", "(").replace("]", ")")
                       for x in data["IPA"]]

        data["TOKENS"] = [" ".join(tokenize_word_reversibly(x))
                          for x in data["IPA"]]

        if args.align or "ALIGNMENT" not in data.columns:
            data["ALIGNMENT"] = data["TOKENS"]

        data["ASJP"] = [" ".join(ipa2asjp(x))
                        for x in data["IPA"]]

        data["COGNATE_SET"] = [
            "" if (i=='nan' or pandas.isnull(i) or not i) else
            list(set(data["COGNATE_SET"])).index(i) + 1
            for i in data["COGNATE_SET"]]

        data["COMMENT"] = [
            x.replace("\n", "; ")
            for x in data["COMMENT"]]

        data.to_csv(
            "tap-unaligned.tsv",
            sep='\t',
            index_label="ID",
            na_rep="",
            encoding='utf-8')

    if args.start <= s['AUTOCODE'] <= args.end or args.start <= s['AUTOALIGN'] <= args.end:
        if args.scores:
            lodict = pickle.load(args.scores)
        else:
            lodict = ...

    if args.start <= s['AUTOCODE'] <= args.end:
        lex = pandas.read_csv(
            "tap-unaligned.tsv", sep="\t", keep_default_na=False, na_values=[""])

        words_dict = {
            concept: {
                language: [
                    tuple(tokens.split()) for tokens in blob["TOKENS"]]
                for language, blob in by_concept.groupby("DOCULECT_ID")}
            for concept, by_concept in lex.groupby("CONCEPT")}

        codes = clust.cognate_code_infomap2(
            words_dict, lodict, gop=-2.5, gep=-1.75, threshold=0.5, method='infomap')

        lex = lex.set_index(["DOCULECT_ID", "CONCEPT", "IPA"])
        lex["AUTO_COGID"] = 0
        for i, similarityset in enumerate(codes):
            for c, l, w in similarityset:
                lex.set_value((l, c, ''.join(w)),
                              "AUTO_COGID",
                              i+1)
                    
        lex.to_csv("tap-cognates.tsv", sep="\t", na_rep="", encoding="utf-8")

    if args.start <= s['RESET'] <= args.end:
        autocognates = pandas.read_csv(
            'tap-cognates.tsv', sep='\t', keep_default_na=False,
            na_values=[""])

        autocognates = autocognates[~(
            pandas.isnull(autocognates["DOCULECT"])
            | pandas.isnull(autocognates["CONCEPT_ID"]))]

        autocognates.sort_values(by="DOCULECT_ID", inplace=True)

        if args.coding is None:
            cognates = autocognates
        else:
            cognates = pandas.read_csv(
                args.coding, sep='\t', keep_default_na=False,
                na_values=[""])

            cognates = cognates[~(
                pandas.isnull(cognates["DOCULECT"])
                | pandas.isnull(cognates["CONCEPT_ID"]))]

            cognates.sort_values(by="DOCULECT_ID", inplace=True)


        cognates["LONG_COGID"] = None
        pairs = set()
        for i, row in list(cognates.iterrows()):
            cognateset = row["COGNATE_SET"]
            reset = cognateset == "nan" or not cognateset or pandas.isnull(
                    cognateset)
            reset |= str(row["COGNATE_SET"]) in args.reset
            reset |= row["DOCULECT_ID"] in args.reset
            reset |= row["CONCEPT"] in args.reset
            if reset:
                autocognates_rows = autocognates[
                        (autocognates["DOCULECT"] == row["DOCULECT"]) &
                        (autocognates["IPA"] == row["IPA"]) &
                        (autocognates["CONCEPT"] == row["CONCEPT"])]["AUTO_COGID"]
                try:
                    cogid = autocognates_rows.iloc[0]
                    representatives = autocognates[
                        autocognates["AUTO_COGID"] == cogid]
                except IndexError:
                    cogid = row["COGNATE_SET"]
                    representatives = cognates[
                        cognates["COGNATE_SET"] == cogid]
                print("Grouping {:} automatically with\n{:}".format(
                    (row["DOCULECT_ID"],
                     row["CONCEPT"],
                     row["IPA"]),
                    representatives[["DOCULECT_ID", "CONCEPT", "IPA", "COGNATE_SET"]]))
            else:
                cogid = row["COGNATE_SET"]
                representatives = cognates[cognates["COGNATE_SET"] == cogid]
            try:
                representative = representatives.iloc[0]
            except IndexError:
                representative = row
                print("Cogid NaN and no automatic coding found for {:}".format(
                    (row["DOCULECT_ID"],
                     row["CONCEPT"],
                     row["IPA"])))

            if row["CONCEPT"] != representative["CONCEPT"]:
                pairs.add((row["CONCEPT"], representative["CONCEPT"]))
            cognates.set_value(i, "LONG_COGID",
                               (representative["DOCULECT_ID"],
                                representative["CONCEPT"],
                                representative["IPA"]))

        print(pairs)
        cognates.to_csv("tap-cognates-mg.tsv",
                        index=False,
                        na_rep="",
                        sep="\t")

    if args.start <= s['MERGE'] <= args.end:
        cognates = pandas.read_csv('tap-cognates-mg.tsv', sep='\t',
                                   keep_default_na=False, na_values=[""])

        subgroup = {
"Kedang-Leubatang": "PEF",
"Kedang-Léuwayang": "PEF",
"Lamaholot-Adonara": "PEF",
"Lamaholot-Baipito": "PEF",
"Lamaholot-Bama": "PEF",
"Lamaholot-Belang": "PEF",
"Lamaholot-Botun": "PEF",
"Lamaholot-Dulhi": "PEF",
"Hewa": "PEF",
"Lamaholot-Horowura": "PEF",
"Lamaholot-Ile Ape": "PEF",
"Lamaholot-Imulolo": "PEF",
"Lamaholot-Kalikasa": "PEF",
"Kedang": "PEF",
"Lamaholot-Kiwangona": "PEF",
"Lamaholot-Lamahora": "PEF",
"Lamaholot-Lamakera": "PEF",
"Lamaholot-Lamalera": "PEF",
"Lamaholot-Lamatuka": "PEF",
"Lamaholot-Lewoeleng": "PEF",
"Lamaholot-Lewokukun": "PEF",
"Lamaholot-Lewolaga": "PEF",
"Lamaholot-Lewolema": "PEF",
"Lamaholot-Lewopenutu": "PEF",
"Lamaholot-Lewotala": "PEF",
"Lamaholot-Lewotobi [Nagaya]": "PEF",
"Lamaholot-Lewotobi": "PEF",
"Lamaholot-Lewuka": "PEF",
"Lamaholot-Merdeka": "PEF",
"Lamaholot-Mingar": "PEF",
"Lamaholot-Mulan": "PEF",
"Lamaholot-Painara": "PEF",
"Lamaholot-Pukaunu": "PEF",
"Lamaholot-Ritaebang": "PEF",
"Lamaholot-Tanjung": "PEF",
"Lamaholot-Waibalun": "PEF",
"Lamaholot-Waiwadan": "PEF",
"Lamaholot-Watan": "PEF",
"Lamaholot-Wuakerong": "PEF",
"Lamaholot-Lewoingu": "PEF",
"Lamaholot-Lerek": "PEF",
"Lamaholot-Central Lembata": "PEF",
"proto-MP-ABVD": "PEF",
"proto-MP-ACD": "PEF",
"proto-MP-ACD 2": "PEF",
"Sika-Maumere": "PEF",
"Sika-Tana Ai": "PEF",}
        short = {"Austronesian": "AN",
                "Timor-Alor-Pantar": "TAP"}
        cognates["DOCULECT"] = [
            "{:s} – {:s} {:s} {:s}".format(
                "X" if pandas.isnull(region) else region,
                "X" if pandas.isnull(family) else short.get(family, family),
                "X" if pandas.isnull(lect) else lect,
                "({:})".format(subgroup[lect]) if lect in subgroup else "")
            for lect, family, region in zip(
                    cognates["DOCULECT"], cognates["FAMILY"], cognates["REGION"])]

        COG_IDs = []
        if args.within_meaning:
            for _, i in cognates[["LONG_COGID", "CONCEPT_ID"]].iterrows():
                i = tuple(i)
                if i not in COG_IDs:
                    COG_IDs.append(i)
            cognates["COGID"] = [
                COG_IDs.index(tuple(x)) + 1
                for _, x in cognates[["LONG_COGID", "CONCEPT_ID"]].iterrows()]
        else:
            for i in cognates["LONG_COGID"]:
                if i not in COG_IDs:
                    COG_IDs.append(i)
            cognates["COGID"] = [
                COG_IDs.index(x) + 1
                for x in cognates["LONG_COGID"]]
        cognates.to_csv("tap-cognates-merged.tsv",
                        index=False,
                        na_rep="",
                        sep="\t")

    if args.start <= s["AUTOALIGN"] <= args.end:
        if args.guide_tree:
            tree = newick.load(args.guide_tree)[0]
        cognates = pandas.read_csv('tap-cognates-merged.tsv', sep='\t',
                                   keep_default_na=False, na_values=[""],
                                   index_col=["DOCULECT_ID", "CONCEPT", "IPA"])
        for c, cognateclass in cognates.groupby("COGID"):
            if args.align or pandas.isnull(
                    cognateclass["ALIGNMENT"]).any() or len(
                    {len(x.split()) for x in cognateclass["ALIGNMENT"]}) > 1:
                
                as_dict = [
                    {(l, c, tuple(row["TOKENS"].split()))
                     for (l, c, t), row in cognateclass.iterrows()}]
                print(as_dict)
                for group, (languages, concepts, algs) in multi_align(
                        as_dict, copy.deepcopy(tree),
                        lodict=MaxPairDict(lodict),
                        gop=-2.5, gep=-1.75).items():
                    for language, concept, alg in zip(
                            languages, concepts, zip(*algs)):
                        print(alg)
                        try:
                            cognates.set_value(
                                (language, concept, ''.join(alg)),
                                "ALIGNMENT",
                                " ".join([a or '-' for a in alg]))
                        except Exception:
                            raise

        cognates.reset_index(inplace=True)
        cognates.to_csv("tap-aligned.tsv",
                        index=True,
                        index_label="ID",
                        na_rep="",
                        sep="\t")
