import pandas


import argparse
parser = argparse.ArgumentParser(description="Add or report cognate codings in word lists")
parser.add_argument("cognate_file", help="The file containing the cognate codes, in EDICTOR format",
                    default="tap-alignment-merged.tsv", nargs="?")
parser.add_argument("--derived_cognate_file", help="Other files containing the cognate codes, in EDICTOR format",
                    default=[], nargs="*")
parser.add_argument("--print", help="Show all differences", action="store_true", default=False)
parser.add_argument("--save", help="Write all differences back to word lists", action="store_true", default=False)
parser.add_argument("--split", help="Split cognate classes that cross concept boundaries",
                    action="store_true", default=False)
args = parser.parse_args()
file = args.cognate_file

cognates = pandas.read_csv(
    file,
    index_col=["CONCEPT", "DOCULECT_ID", "VALUE"],
    sep="\t")

cognates["COGID"] = cognates["COGID"].astype('str')

for cogid, entries in cognates.groupby("COGID"):
    code = entries.index[0]
    for index in entries.index:
        try:
            if args.split:
                cognates.set_value(index, "COGID", str(index[0])+"-"+str(code))
            else:
                cognates.set_value(index, "COGID", str(code))
        except AttributeError:
            continue

cognates.sort_index(inplace=True)

while cognates.index.duplicated().any():
    cognates = cognates[~cognates.index.duplicated()]

for file in args.derived_cognate_file:
    df = pandas.read_csv(
        file,
        index_col=["CONCEPT", "DOCULECT_ID", "VALUE"],
        sep="\t")
    while df.index.duplicated().any():
        df = df[~df.index.duplicated()]
    cogids = df["COGID"].dropna().astype('str')
    cogids.sort_index(inplace=True)
    for cogid, entries in cogids.groupby(cogids):
        code = entries.index[0]
        for index in entries.index:
            if args.split:
                cognates.set_value(index, file, str(index[0])+"-"+str(code))
            else:
                cognates.set_value(index, file, str(code))

cognates.sort_index(inplace=True)

word_lists = {}
for i, line in cognates.iterrows():
    original_file = line["ORIGINAL_FILE"]
    word_list = word_lists.get(original_file)

    if word_list is None:
        try:
            word_list = pandas.read_csv(
                original_file,
                index_col=["English", "Language_ID", "Value"],
                dtype={"Alignment": str},
                sep="\t")
        except OSError:
            continue
        word_list["Cognate Set"] = word_list["Cognate Set"].astype('str')
        word_lists[original_file] = word_list
    
    # Compare cognate IDs
    cogid_precoding = line["COGID"]
    cogid_postcoding = line["COGID"]

    for file in args.derived_cognate_file:
        if pandas.isnull(line[file]):
            continue
        elif line[file] == cogid_precoding:
            continue
        elif line[file] == cogid_postcoding:
            continue
        elif cogid_postcoding == cogid_precoding:
            cogid_postcoding = line[file]
        elif args.save:
            raise ValueError("Original word list got changed in two different ways:",
                             line, cogid_postcoding, line[file])
        else:
            print("Divergence: {:} → {:} / {:} ({:})".format(
                    cogid_precoding, 
                    cogid_postcoding,
                    line[file],
                    file))

    try:
        cogid_old = word_list["Cognate Set"][i]
    except KeyError:
        print(i)
        continue
    
    try:
        cogid_old = cogid_old.iloc[0]
    except AttributeError:
        pass
    
    if (cogid_postcoding != cogid_old):
        word_list.set_value(i, "Cognate Set", cogid_postcoding)
        if args.print and not pandas.isnull(cogid_old):
            print(i, cogid_old, type(cogid_old), "→ ", cogid_postcoding, type(cogid_postcoding))

    # Compare alignments
    alignment_coding = line["ALIGNMENT"]
    alignment_old = word_list["Alignment"][i]
    
    try:
        alignment_old = alignment_old.iloc[0]
    except AttributeError:
        pass
    
    if (alignment_coding != alignment_old):
        word_list.set_value(i, "Alignment", alignment_coding)
        if args.print and not pandas.isnull(alignment_old):
            print(i, alignment_old, "→", alignment_coding)

if args.save:
    for file, data in word_lists.items():
        word_lists[file].to_csv(
            file,
            sep="\t")
            
