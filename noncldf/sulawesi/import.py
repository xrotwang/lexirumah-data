import json
from pathlib import Path
from collections import OrderedDict

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
new_form_id = max(int(f["ID"]) for f in new_forms) + 1

header = None
for row in xlrd.open_workbook(str(Path(__file__).parent / "Buton Muna Wordlists.xlsx")).sheet_by_index(0).get_rows():
    row = [cell.value for cell in row][1:]
    if row[1] == "Informant":
        row[0] = "Lect"
        header = row
        data_start = header.index("kepala")
        metadata = header[:data_start - 1]
        conceptlist = OrderedDict([concepts.get(g, (None, None))
                                   for g in header[data_start:]])
    elif header and not row[4]:
        continue
    elif header:
        metadata = dict(zip(metadata, row))

        words = {c: value.split("/") for c, value in zip(conceptlist, row[data_start:])
                 if c
                 if value}

        metadata["Lect"], lect_id = alternative_names.get(metadata["Lect"], (metadata["Lect"], None))
        if lect_id:
            lect = gl.languoid(lect_id[:8])
        else:
            n, lects = search_langs(
                gl, lect_id[:8] if lect_id else metadata['Lect'])
            try:
                lect = gl.languoid(lects[0].id)
            except IndexError:
                print(metadata["Lect"], lect_id)
                raise
        print(metadata['Lect'], lect)
        p = lect
        try:
            while True:
                if p.latitude:
                    lat = p.latitude
                    lon = p.longitude
                    print(lat, lon)
                    break
                else:
                    p = p.parent
        except AttributeError:
            pass
        # query = "Kecamatan " + metadata["Kecamatan"].strip("?") + ", Indonesia"
        # location = geonames.geocode(query)
        # try:
        #     assert -7 < location.latitude < -1
        #     assert 120 < location.longitude < 130
        #     lat = location.latitude
        #     lon = location.longitude
        #     print(lat, lon)
        # except (AttributeError, AssertionError):
        #     print(query)
        lect_id = lect_id or lect.glottocode
        if lect_id not in [l["ID"] for l in new_lects]:
            new_lects.append({
                "ID": lect_id,
                "Name": metadata["Lect"],
                "Family": "Austronesian",
                "Latitude": lat,
                "Longitude": lon,
                "Region": get_region(lat, lon),
                "Glottocode": lect.glottocode,
                "Iso": metadata["EthCode"],
                "Culture": None,
                "Description": None,
                "Orthography": ["p/general"],
                "Comment": (metadata["Notes-classification"] or "")
                + "Locations estimated from Kecamatan and/or Glottolog"})

        source = metadata["Linguist / Source"]
        source_key = identifier(source)
        try:
            new_sources.add_entry(
                source_key,
                pybtex.database.Entry(
                    "incollection",
                    fields={"title": source,
                            "editor": "Mead, David",
                            "quality": metadata["Quality"]}))
        except pybtex.database.BibliographyDataError:
            pass

        for concept, forms in words.items():
            for form in forms:
                if form == "—":
                    # Missing form
                    continue
                new_forms.append({
                    "ID": str(new_form_id),
                    "Lect_ID": lect_id,
                    "Concept_ID": concept,
                    "Form_according_to_Source": form,
                    "Source": [source_key],
                    "Comment": conceptlist.get(concept),
                })
                new_form_id += 1

lr["LanguageTable"].write(new_lects)
lr["FormTable"].write(new_forms)
lr.sources.add(new_sources)
lr.write_sources()
