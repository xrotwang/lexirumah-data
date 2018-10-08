import bisect
import random
import itertools
import collections

import lingpy
import lingpy.compare.partial

from . import get_dataset

lexirumah = get_dataset()

lex = lingpy.compare.partial.Partial("lexstats.tsv",
        col="lect_id", row="concept_id", segments="segments", transcription="form")

assigned_to_cognateset = {}
for entry in lexirumah["CognateTable"].iterdicts():
    assigned_to_cognateset[entry["Form_ID"]] = entry["Cognateset_ID"]

lex_by_id = {
    lex[row][lex.header["id"]]: row
    for row in lex}

familiar_languages = {
    "koto1251", "lama1277-kalik", "alor1247-besar", "alor1247-pandai",
    "lama1277-kalik", "sika1262-tanai", "abui1241-takal", "kaer1234",
    "pura1258", "adan1251-otvai", "kelo1247-bring"}

indonesian_loans = set()

forms_by_concept = {}
for form in lexirumah["FormTable"].iterdicts():
    id = form["ID"]
    concept = form["Concept_ID"]
    row = lex_by_id.get(str(id))

    segments = form["Segments"]
    if not segments:
        continue
    lect = form["Lect_ID"]

    if lect == "indo1316-lexi":
        indonesian_loans.add(assigned_to_cognateset.get(id))
    if lect not in familiar_languages:
        continue

    forms_by_concept.setdefault(concept, []).append(
        (id,
         lect,
         segments,
         assigned_to_cognateset.get(id),
         row,
         concept)
    )

lects = collections.defaultdict(
    lambda: "Austronesian",
    {row["ID"]: row["Family"] for row in lexirumah["LanguageTable"].iterdicts()})

pairs = {True: [],
         False: []}
distances = {True: [],
             False: []}
for concept, forms in forms_by_concept.items():
    for f1, f2 in itertools.combinations(forms, 2):
        if f1[2] == f2[2]:
            continue
        same_class = (f1[3] == f2[3] and f1[3] is not None)
        if not same_class and random.random() > 0.1:
            continue
        if f1[3] in indonesian_loans or f2[3] in indonesian_loans:
            continue
        if f1[4] and f2[4]:
            _, _, score = lex.align_pairs(f1[4], f2[4], pprint=False)
        else:
            _, _, score = lingpy.align.pairwise.pw_align(
                f1[2], f2[2],
                distance=True)
        i = bisect.bisect(distances[same_class], score)
        distances[same_class].insert(i, score)
        pairs[same_class].insert(i, (f1, f2))

def format_output(f1, f2, d, file):
    id1, lect1, s1, cogid1, row1, concept1 = f1
    id2, lect2, s2, cogid2, row2, concept2 = f2

    if not (lect1 in familiar_languages and lect2 in familiar_languages):
        return

    print(concept1, d,
          lect1, lects[lect1][:2], " ".join(s1), row1,
          lect2, lects[lect2][:2], " ".join(s2), row2,
          sep="\t", file=file)

with open("check_these.tsv", "w") as out:
    print("concept1", "d",
          "Lect 1", "F1", "Form1", "ID1",
          "Lect 2", "F2", "Form2", "ID2",
          sep="\t", file=out)
    for (f1, f2), d in zip(pairs[True], distances[True]):
        format_output(f1, f2, d, out)
    print("concept1", "d",
          "Lect 1", "F1", "Form1", "ID1",
          "Lect 2", "F2", "Form2", "ID2",
          sep="\t", file=out)
    for (f1, f2), d in zip(pairs[False], distances[False]):
        format_output(f1, f2, d, out)

