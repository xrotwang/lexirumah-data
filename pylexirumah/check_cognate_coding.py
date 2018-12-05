#!/usr/bin/env python

"""Compare cognates in a CLDF Wordlist with a pairwise gold standard"""

from pycldf.util import Path
import argparse

import csv
from pylexirumah.util import get_dataset, cognate_sets


def pprint_form(form_id):
    print("{:8} {:20s} {:20s} {:s}".format(
        forms[form_id][c_id],
        forms[form_id][c_lect],
        forms[form_id][c_concept],
        " ".join(forms[form_id][c_segm])))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("gold",
                        type=Path,
                        help="A CSV file listing pairs of forms and whether"
                        " they should be considered cognates or not.")
    parser.add_argument("--column-id-1", default="ID1",
                        help="Header of first column containing Form_IDs in"
                        " GOLD (default: ID1)")
    parser.add_argument("--column-id-2", default="ID2",
                        help="Header of second column containing Form_IDs in"
                        " GOLD (default: ID2)")
    parser.add_argument("--gold-column", default="Cognate",
                        help="Header of column containing cognate judgements"
                        " as float values between -1 [not cognate] and 1"
                        " cognate (default: Cognate)")
    parser.add_argument("codings",
                        type=Path,
                        help="A CLDF dataset with cognate codes")
    parser.add_argument("--lingpy", action="store_true",
                        default=False,
                        help="The data is in LingPy's format, not CLDF.")
    parser.add_argument("--verbose", action="store_true",
                        default=False,
                        help="Output the forms which do not match.")
    parser.add_argument("--ssv", default=False,
                        action="store_true",
                        help="Output one line, not many")
    args = parser.parse_args()

    if args.lingpy:
        import lingpy
        dataset = lingpy.LexStat(str(args.codings))
        forms = {row:
            {e: dataset[row][dataset.header[e]]
             for e in dataset.entries
             if e in dataset.header}
            for row in dataset}
        codings = {
            form: row["partial_ids"]
            for form, row in forms.items()}
        c_id = "reference"
        c_lect = "doculect"
        c_concept = "concept"
        c_segm = "tokens"
    else:
        dataset = get_dataset(args.codings)
        cognatesets = cognate_sets(dataset)
        codings = {
            form: code
            for code, forms in cognatesets.items()
            for form in forms}
        c_id = dataset["FormTable", "id"].name
        c_lect = dataset["FormTable", "languageReference"].name
        c_concept = dataset["FormTable", "parameterReference"].name
        c_segm = dataset["FormTable", "segments"].name

        forms = {row[c_id]: row for row in dataset["FormTable"].iterdicts()}

    if args.verbose:
        message = print
    else:
        def message(*args):
            pass
        def pprint_form(form):
            pass

    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0

    for line in csv.DictReader(args.gold.open()):
        try:
            judgement = float(line[args.gold_column])
        except ValueError:
            continue

        form1 = int(line[args.column_id_1])
        form2 = int(line[args.column_id_2])
        c1 = codings.get(form1)
        c2 = codings.get(form2)
        if c1 is None or c2 is None:
            # These forms are not coded. This is bad.
            false_negatives += 1
        elif judgement > 0:
            if c1==c2:
                # When judgement is positive, we want the cognate classes to be the same. This is fine.
                true_positives += 1
            else:
                # These forms are in disagreement with the gold standard!
                false_negatives += 1
                message(form1, "should be cognate with", form2)
                pprint_form(form1)
                pprint_form(form2)
        else:
            if c1==c2:
                # These forms are in disagreement with the gold standard!
                false_positives += 1
                message(form1, "should not be cognate with", form2)
                pprint_form(form1)
                pprint_form(form2)
            else:
                # When judgement is positive, we want the cognate classes to be the same. This is fine.
                true_negatives += 1

    end = " " if args.ssv else "\n"
    print(args.codings, end=end)
    print("    Data:", "T", "F", end=end)
    print("Target: T", true_positives, false_negatives, end=end)
    print("Target: F", false_positives, true_negatives, end=end)
    print("F-Score:",
          2 * true_positives / (2 * true_positives + false_positives + false_negatives))


