import pandas
import os, os.path


import argparse
parser = argparse.ArgumentParser(description="Add or report cognate codings in word lists")
parser.add_argument("cognate_file", help="The files containing the cognate codes, in EDICTOR format",
                    default=["tap-aligned.tsv"], nargs="*")
parser.add_argument("--print", help="Show all differences", action="store_true", default=False)
parser.add_argument("--save", help="Write all differences back to word lists", action="store_true", default=False)
args = parser.parse_args()

path = "datasets/"
datafiles = [file for file in os.listdir(path)
             if file.endswith(".tsv")]
cognates = pandas.read_csv(
        os.path.join(path, datafiles[0]),
        index_col=["Feature_ID", "Language_ID", "Value"],
        sep="\t")[["Cognate Set"]]
cognates.columns = ["datasets"]
cognates = cognates.dropna()
while cognates.index.duplicated().any():
        cognates = cognates[~cognates.index.duplicated()]
for file in datafiles[1:]:
    for i, cogid in pandas.read_csv(
        os.path.join(path, file),
        index_col=["Feature_ID", "Language_ID", "Value"],
        sep="\t")["Cognate Set"].items():
        if pandas.isnull(cogid) or i[2] in ['-']:
            pass
        else:
            cognates.set_value(i, "datasets", cogid)

for file in args.cognate_file:
    df = pandas.read_csv(
        file,
        index_col=["CONCEPT_ID", "DOCULECT_ID", "VALUE"],
        sep="\t")
    while df.index.duplicated().any():
        df = df[~df.index.duplicated()]
    cogids = df["COGID"].dropna()
    for cogid, entries in cogids.groupby(cogids):
        for index in entries.index:
            cognates.set_value(index, file, str(entries.index[0]))


cognates = cognates.sort_index()

print(cognates.to_string())

