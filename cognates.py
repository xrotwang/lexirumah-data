#!/usr/bin/env python

"""Transform word list data into an input file for edictor.

Rename columns of all_data.tsv to the ones expected by edictor.
Optionally, also use lingpy for automated cognate coding and
alignment.

"""

import pandas
import argparse
from lingpy import LexStat, Alignments


def cognate_detect(segments):
    """Perform automatic cognate detection.
    
    Based on the phoneme segmentation described by `segments`, cluster
    the forms into cognate classes.

    """
    ...


parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("filename", default="all_data.tsv", nargs="?",
                    help="Input filename containing word lists")
parser.add_argument("--keep-orthographic", default=False, action='store_true',
                    help="Do not remove orthographic variants")
args = parser.parse_args()

data = pandas.io.parsers.read_csv(
    args.filename,
    sep="," if args.filename.endswith(".csv") else "\t",
    na_values=[""],
    keep_default_na=False,
    encoding='utf-8')

if not args.keep_orthographic:
    data = data[~data["Language_ID"].str.endswith("-o")]

replacement = {
    'Feature_ID': 'CONCEPT_ID',
    'Language_ID': 'DOCULECT_ID',
    'Cognate Set': 'COGNATE_SET',
    'English': 'CONCEPT',
    'Language name (-dialect)': 'DOCULECT',
    'Value': 'IPA'}
cols = [replacement.get(c, c.upper()) for c in data.columns]
data.columns = cols


def alignment(data):
    """Generate alignment-like entries from a sequence of forms.

    Take the columns IPA (of forms) and ALIGNMENT (of
    space-separated components of alignments – IPA symbols, markers or
    gaps) and generate ALIGNMENT where it does not make sense.

    """
    for form, alignment in data[["IPA", "ALIGNMENT"]].values:
        form = str(form).replace("\n", ";")
        alignment = alignment.replace("\n", ";")
        if alignment in ("", "nan"):
            yield " ".join(list(str(form)))
        else:
            if list(form) != [
                    x
                    for x in alignment.split()
                    if x != "-"]:
                yield " ".join(list(str(form)))
            else:
                yield alignment
    

data["ALIGNMENT"] = list(alignment(data))

data["COGNATE_SET"] = [
    list(set(data["COGNATE_SET"])).index(i)
    for i in data["COGNATE_SET"]]

data["COMMENT"] = [
    x.replace("\n", "; ")
    for x in data["COMMENT"]]

data = data[~pandas.isnull(data["IPA"])]

data["TOKENS"] = data["IPA"].str.replace(" ", "")

data.to_csv(
    "unaligned.tsv",
    sep='\t',
    index_label="ID",
    na_rep="",
    encoding='utf-8')

lex = LexStat("unaligned.tsv")
lex.get_scorer(preprocessing=False, runs=10000, ratio=(2, 1), vscale=1.0)
lex.cluster(cluster_method='upgma',
            method='lexstat',
            ref='auto_cogid',
            threshold=0.8)
lex.output("tsv", filename="tap-cognates", ignore="all", prettify=True)

cognates = pandas.read_csv(
    'tap-cognates.tsv', sep='\t', keep_default_na=False, na_values=[""],
    skiprows=[0, 1, 2])

cognates["LONG_COGID"] = None
for i, row in cognates.iterrows():
    if (pandas.isnull(row["COGNATE_SET"]) or row["COGNATE_SET"] == "nan"):
        cogid = row["AUTO_COGID"]
        representative = (cognates["AUTO_COGID"] == cogid).argmin()
        cognates.set_value(i, "LONG_COGID",
                           cognates["COGNATE_SET"][representative])
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

cognates.sort_values(by="DOCULECT", inplace=True)

COG_IDs = []
for i in cognates["LONG_COGID"]:
    if i not in COG_IDs:
        COG_IDs.append(i)
cognates["COGID"] = [COG_IDs.index(x) for x in cognates["LONG_COGID"]]
cognates.to_csv("tap-cognates-merged.tsv",
                index=False,
                na_rep="",
                sep="\t")


# align data
alm = Alignments('tap-cognates-merged.tsv', ref='COGID', segments='SEGMENTS',
                 transcription='IPA', alignment='SEGMENTS')
alm.align(override=True, alignment='AUTO_ALIGNMENT')
alm.output('tsv', filename='tap-aligned', ignore='all', prettify=False)

alignments = pandas.read_csv(
    'tap-aligned.tsv',
    args.filename,
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

alignments = alignments[~alignments["Language_ID"].str.endswith("-o")]
alignments.to_csv("tap-alignments-merged.tsv",
                  index=False,
                  na_rep="",
                  sep="\t")
