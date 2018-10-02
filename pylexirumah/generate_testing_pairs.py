import bisect
import random
import itertools

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

forms_by_concept = {}
for form in lexirumah["FormTable"].iterdicts():
    id = form["ID"]
    concept = form["Concept_ID"]
    row = lex_by_id.get(str(id))

    segments = form["Segments"]
    if not segments:
        continue

    forms_by_concept.setdefault(concept, []).append(
        (id,
         form["Lect_ID"],
         segments,
         assigned_to_cognateset.get(id),
         row,
         concept)
    )

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
        if f1[4] and f2[4]:
            _, _, score = lex.align_pairs(f1[4], f2[4], pprint=False)
        else:
            _, _, score = lingpy.align.pairwise.pw_align(
                f1[2], f2[2],
                distance=True)
        i = bisect.bisect(distances[same_class], score)
        distances[same_class].insert(i, score)
        pairs[same_class].insert(i, (f1, f2))
        print(f1[2], f2[2], score)

with open("check_these.csv", "w") as out:
    for i in range(int(len(pairs[True]) ** 0.5)):
        f1, f2 = pairs[True][-(i ** 2) - 1]
        print(*(f1+f2), sep="\t", file=out)
    print("#", file=out)
    for i in range(int(len(pairs[False]) ** 0.5)):
        f1, f2 = pairs[False][i ** 2]
        print(*(f1+f2), sep="\t", file=out)
