"""Add or report cognate coding changes in word lists."""
import pandas
import difflib


from process_data import write_normalized_data


import argparse
parser = argparse.ArgumentParser(
    description="Add or report cognate codings in word lists")
parser.add_argument(
    "cognate_file",
    help="The file containing the cognate codes, in EDICTOR format",
    default="tap-aligned.tsv", nargs="?")
parser.add_argument(
    "--derived_cognate_file",
    help="Other files containing the cognate codes, in EDICTOR format",
    default=[], nargs="*")
parser.add_argument(
    "--print",
    help="Show all differences", action="store_true", default=False)
parser.add_argument(
    "--save",
    help="Write all differences back to word lists",
    action="store_true", default=False)
parser.add_argument(
    "--split",
    help="Split cognate classes that cross concept boundaries",
    action="store_true", default=False)
parser.add_argument(
    "--copy-columns",
    help="Copy these columns",
    action="append", default=[])
parser.add_argument(
    "--bad-cogid", action="append", default=[],
    help="Untrusted cogids in COGNATE_FILE, which should be ignored")
args = parser.parse_args()
file = args.cognate_file

cognates = pandas.read_csv(
    file,
    index_col=["CONCEPT", "DOCULECT_ID", "VALUE"],
    na_values="",
    keep_default_na=False,
    sep="\t")

cognates["COGID"] = cognates["COGID"].astype('str')

cognates.sort_index(inplace=True)

# Generate form-based (and therefore more stable) cognate IDs
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

# Remove duplicate Concept-Language-Form combinations
while cognates.index.duplicated().any():
    cognates = cognates[~cognates.index.duplicated()]

# Read the derived cognate codings into other columns of the same data frame
for file in args.derived_cognate_file:
    df = pandas.read_csv(
        file,
        index_col=["CONCEPT", "DOCULECT_ID", "VALUE"],
        na_values="",
        keep_default_na=False,
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

# Write cognate codings back to original word lists

word_lists = {}
# Cache opened word list data frames

changes = {}
problems = []
for i, line in cognates.iterrows():
    i = i[0], i[1], i[2]
    original_file = line["SOURCE"]
    word_list = word_lists.get(original_file)

    # If we have not opened that word list yet, do so now.
    if word_list is None:
        try:
            word_list = pandas.read_csv(
                original_file,
                index_col=["English", "Language_ID", "Value"],
                dtype={"Alignment": str},
                na_values="",
                keep_default_na=False,
                sep="\t")
        except OSError:
            continue
        except ValueError:
            if pandas.isnull(original_file):
                problems.append((i, line))
                continue
            else:
                raise ValueError("Row {:} contained absent 'SOURCE' pointer {:}".format(
                    i, original_file), line)
        word_list["Cognate Set"] = word_list["Cognate Set"].astype('str')
        word_lists[original_file] = word_list
    
    # Compare cognate IDs
    cogid_precoding = line["COGID"]
    cogid_postcoding = line["COGID"]

    # Compare what the derived cognate files did (if anything)
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
            raise ValueError(
                "Original word list got changed in two different ways:",
                line, cogid_postcoding, line[file])
        else:
            print("Divergence: {:} → {:} / {:} ({:})".format(
                cogid_precoding,
                cogid_postcoding,
                line[file],
                file))

    # Compare the cognate coding reflected in the word lists.
    try:
        cogid_old = word_list["Cognate Set"][i]
    except KeyError:
        try:
            known_forms = word_list.reset_index(level=2).loc[i[:2]]
            sim = -1
            for _, word in known_forms.iterrows():
                s = difflib.SequenceMatcher(
                    a=word["Value"],
                    b=i[2]).ratio()
                if s >= sim:
                    candidate = word["Value"]
                    sim = s
        except AttributeError:
            candidate = known_forms["Value"]
        except (KeyError, TypeError):
            print(
                "Word form {:} not found in word list {:}."
                " Assuming it got deleted".format(
                    i, original_file))
            continue
        print(
            "Word form {:} not found in word list {:}."
            " Assuming it got corrected to {:}".format(
                i, original_file, candidate))
        i = i[:2] + (candidate,)
        cogid_old = word_list["Cognate Set"][i]
    
    try:
        # We might have duplicates in the word list. In that case,
        # take the first instance.
        cogid_old = cogid_old.iloc[0]
    except AttributeError:
        pass

    if cogid_postcoding in args.bad_cogid:
        cogid_postcoding = None
    elif (cogid_postcoding != cogid_old):
        changes.setdefault(
            (cogid_old, cogid_postcoding),
            []).append(i)
        word_list.set_value(i, "Cognate Set", cogid_postcoding)

    for column in args.copy_columns:
        # Compare alignments
        alignment_coding = line[column.upper()]
        alignment_old = word_list[column.title()][i]

        try:
            alignment_old = alignment_old.iloc[0]
        except AttributeError:
            pass

        if (alignment_coding != alignment_old):
            word_list.set_value(i, column.title(), alignment_coding)
            if args.print and not pandas.isnull(alignment_old):
                print("{:} changed: {:} ({:}) → {:} ({:})".format(
                    column.title(),
                    alignment_old,
                    type(alignment_old),
                    alignment_coding,
                    type(alignment_coding)))

if args.print:
    for (cogid_old, cogid_postcoding), forms in changes.items():
        print("The following items were moved from class {:40} to {:40}:".format(
            cogid_old, cogid_postcoding))
        for form in forms:
            print("   ", form)

if args.save:
    for file, data in word_lists.items():
        write_normalized_data(data, file)
