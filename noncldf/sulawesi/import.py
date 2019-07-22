import json
from pathlib import Path
from collections import OrderedDict, Counter

import xlrd

import pybtex
import pyglottolog
from pyglottolog.fts import search_langs

from pylexirumah import get_dataset
from pylexirumah.geo_lookup import geonames, get_region
from pylexirumah.util import identifier

gl = pyglottolog.Glottolog(Path(pyglottolog.__file__).parent.parent.parent.parent / "glottolog")

__file__ = "this"

lr = get_dataset()
# The concepts.json matches Indonesian glosses to LexiRumah concepts and
# necessary comments. Most of the matches there were found automatically
# through very close matches of the Indonesian or English gloss, with some
# manual corrections.
concepts = json.load((Path(__file__).parent / "concepts.json").open())

new_sources = pybtex.database.BibliographyData()
new_lects = list(lr["LanguageTable"].iterdicts())
new_forms = list(lr["FormTable"].iterdicts())
synonym_counts = Counter()

header = None
for row in xlrd.open_workbook(str(Path(__file__).parent / "Buton Muna Wordlists.xlsx")).sheet_by_index(0).get_rows():
    row = [cell.value for cell in row]
    if "Informant" in row:
        header = row
        data_start = header.index("kepala")
    elif header and not row[4]:
        continue
    elif header and not header[0]:
        header = [h or r for h, r in zip(header, row)]
        metadata = header[:data_start - 1]
        conceptlist = OrderedDict([concepts.get(g, (None, None))
                                   for g in header[data_start:]])
    elif header:
        metadata = dict(zip(metadata, row))

        if not metadata['usethis one (or these ones) of duplicate']:
            continue

        words = {c: value.split("/") for c, value in zip(conceptlist, row[data_start:])
                 if c
                 if value}

        lect_id = metadata["ID"]
        if lect_id not in [l["ID"] for l in new_lects]:
            new_lects.append(metadata)

        source = metadata["Source"]
        source_key = identifier(source)

        for concept, forms in words.items():
            for form in forms:
                if form == "—":
                    # Missing form
                    continue
                synonym_counts[(lect_id, concept)] += 1
                new_forms.append({
                    "ID": "{:}-{:}-{:}".format(lect_id, concept, synonym_counts[(lect_id, concept)]),
                    "Lect_ID": lect_id,
                    "Concept_ID": concept,
                    "Form_according_to_Source": form,
                    "Source": [source_key],
                    "Comment": conceptlist.get(concept),
                })

lr["LanguageTable"].write(new_lects)
lr["FormTable"].write(new_forms)
lr.sources.add(new_sources)
lr.write_sources()
