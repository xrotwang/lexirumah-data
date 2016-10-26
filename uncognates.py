import pandas


import argparse
parser = argparse.ArgumentParser(description="Add or report cognate codings in word lists")
parser.add_argument("cognate_file", help="The file containing the cognate codes, in EDICTOR format",
                    default="tap-aligned.tsv", nargs="?")
parser.add_argument("--print", help="Show all differences", action="store_true", default=False)
parser.add_argument("--save", help="Write all differences back to word lists", action="store_true", default=False)
args = parser.parse_args()
file = args.cognate_file

cognates = pandas.read_csv(
    file,
    index_col=["CONCEPT_ID", "DOCULECT_ID", "VALUE"],
    sep="\t")

word_lists = {}
for i, line in cognates.iterrows():
    original_file = line["ORIGINAL_FILE"]
    word_list = word_lists.get(original_file)

    if word_list is None:
        try:
            word_list = pandas.read_csv(
                original_file,
                index_col=["Feature_ID", "Language_ID", "Value"],
                dtype={"Alignment": str},
                sep="\t")
        except OSError:
            continue
        word_lists[original_file] = word_list
    
    # Compare cognate IDs
    cogid_coding = line["COGID"]
    try:
        cogid_old = word_list["Cognate Set"][i]
    except KeyError:
        print(i)
        continue
    
    try:
        cogid_old = cogid_old.iloc[0]
    except AttributeError:
        pass
    
    if (cogid_coding != cogid_old):
        word_list.set_value(i, "Cognate Set", cogid_coding)
        if args.print and not pandas.isnull(cogid_old):
            print(i, cogid_old, type(cogid_old), "→", cogid_coding, type(cogid_coding))

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
            
