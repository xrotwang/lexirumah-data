#!/usr/bin/env python

from bisect import bisect

from clldutils.path import Path
from .util import glottolog_clade, get_dataset, lexirumah_glottocodes

repository = (Path(__file__).parent.parent /
              "cldf" / "Wordlist-metadata.json")

lexirumah = get_dataset(repository)
cognateclass_by_form = {}
for cognate in lexirumah["CognateTable"].iterdicts():
    cognateclass_by_form[cognate["Form_ID"]] = cognate["Cognateset_ID"]

groups = [set(lexirumah_glottocodes(lexirumah)),
          glottolog_clade("lama1292", lexirumah),
          glottolog_clade("alor1247", lexirumah)]
groups[1] -= groups[2]
groups[0] -= groups[1]
groups[0] -= groups[2]

attested_cognate_sets = {}

cognates_by_class = {}
for form in lexirumah["FormTable"].iterdicts():
    concept = form["Concept_ID"]
    lect = form["Lect_ID"]
    cognates_by_class.setdefault(
        cognateclass_by_form.get(form["ID"]), set()).add(
        (concept, lect, form["Form"]))
    for g, group in enumerate(groups):
        if lect in group:
            concept_classes = attested_cognate_sets.setdefault(
                concept, [set() for g_ in groups])[g]
            concept_classes.add(cognateclass_by_form.get(form["ID"]))

concepts = []
concept_stability = []
for concept, concept_classes in attested_cognate_sets.items():
    order = len(
        set.union(*concept_classes))
    i = bisect(concept_stability, order)
    concepts.insert(i, concept)
    concept_stability.insert(i, order)

for concept in concepts:
    concept_classes = attested_cognate_sets[concept][1:]
    intersection = set.intersection(*concept_classes)
    if set.union(*concept_classes) == intersection:
        del attested_cognate_sets[concept]
    else:
        print(concept)
        for cognateclass in intersection:
            print("", cognates_by_class[cognateclass])
        for g, classes in enumerate(concept_classes):
            print("", g)
            for cognateclass in classes - intersection:
                print(" ", cognates_by_class[cognateclass])
