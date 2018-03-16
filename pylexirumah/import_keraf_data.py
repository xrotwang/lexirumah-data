import csv
import pathlib

import pycldf

from util import resolve_brackets

dataset = pycldf.Dataset.from_metadata("../cldf/Wordlist-metadata.json")

concepts_by_indonesian = {}
concepts_by_english = {}
for row in dataset["ParameterTable"]:
    if row["Indonesian"]:
        ind = row["Indonesian"].lower()
        concepts_by_indonesian[ind.strip()] = row
        if ")" in ind:
            for i in resolve_brackets(ind):
                concepts_by_indonesian[i.strip()] = row
    concepts_by_english[row["English"].strip("?")] = row
    if row["Comment"] and "Keraf" in row["Comment"]:
        if "”" in row["Comment"]:
            keraf_concept = row["Comment"].split("”")[0].split("“")[1]
            concepts_by_indonesian[keraf_concept] = row
        else:
            print(row["ID"], row["Comment"])

fix = {"j": "dʒ",
       " ": "_",
       "y": "j"}

path = pathlib.Path("../noncldf/keraf")
keraf_concepts = {}
forms = [row for row in dataset["FormTable"].iterdicts()
         if "keraf1978" not in row["Source"]]
id = forms[-1]["ID"]
for file in path.glob("*.tsv"):
    if not keraf_concepts:
        with file.open() as kerafwordlist:
            for row in csv.DictReader(kerafwordlist, dialect="excel-tab"):
                gloss = row["gloss"].split(".", 1)[1].lower().strip()
                if gloss in concepts_by_indonesian:
                    concept = concepts_by_indonesian[gloss]["ID"]
                    pass
                elif row['translation'] in concepts_by_english:
                    concept = concepts_by_english[row["translation"]]["ID"]
                elif "to " + row['translation'] in concepts_by_english:
                    concept = concepts_by_english["to " + row["translation"]]["ID"]
                else:
                    raise ValueError
                keraf_concepts[row["gloss"].strip()] = concept
    fiveletters = "".join(file.name.lower().split())[:5]
    with file.open() as kerafwordlist:
        for row in csv.DictReader(kerafwordlist, dialect="excel-tab"):
            id += 1
            if row["transcription"].strip().strip("—"):
                forms.append({
                    "ID": id,
                    "Lect_ID": "lama1277-{:}".format(fiveletters),
                    "Concept_ID": keraf_concepts[row["gloss"].strip()],
                    "Form": row["transcription"],
                    "Segments": [fix.get(s, s) for s in row["transcription"]],
                    "Comment": row["comment"] or None,
                    "Source": ["keraf1978"]
                })

dataset["FormTable"].write(forms)
