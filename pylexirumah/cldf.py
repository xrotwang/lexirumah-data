import re
import math

import csv
import json

import sys
import argparse

from clldutils.path import Path
from pycldf.sources import Source
from pycldf.dataset import Wordlist
from clldutils.csvw.metadata import Column

from pyclpa.base import Sound
from segment import tokenize_clpa, CLPA

from geo_lookup import get_region
from pybtex.database import BibliographyData, Entry

class C:
    address = "ENUS"
def get_region(lat, lon):
    return C()

REPLACE = {
    " ": "_",
    '’': "'",
    '-': "_",
    '.': "_",
    "'": "'",
    "*": "",
    '´': "'",
    'µ': "_",
    'ǎ': "a",
    '̃': "_",
    ',': "ˌ",
    '=': "_",
    '?': "ʔ",
    'ā': "aː",
    "ä": "a",
    'Ɂ': "ʔ",
    "h̥": "h",
    "''": "'",
    "á": "'a",
    'ū': "uː",
}


def identifier(string):
    return re.sub('(\W|^(?=\d))+','_', string).strip("_")


def resolve_brackets(string):
    """Resolve a string into all description without brackets

    For a `string` with matching parentheses, but without nested parentheses,
    yield every combination of the contents of any parenthesis being present or
    absent.

    >>> list(resolve_brackets("no brackets"))
    ["no brackets"]

    >>> sorted(list(resolve_brackets("(no )bracket(s)")))
    ["bracket", "brackets", "no bracket", "no brackets"]

    """
    if "(" in string:
        opening = string.index("(")
        closing = string.index(")")
        for form in resolve_brackets(string[:opening] + string[closing+1:]):
            yield form
        for form in resolve_brackets(string[:opening] +string[opening+1:closing] + string[closing+1:]):
            yield form
    else:
        yield string


def main(path, original, concept_id, foreign_key, encoding="utf-8"):
    dataset = Wordlist.from_metadata(path)

    dataset_metadata = json.load(original.parent.joinpath("metadata.json").open())
    corresponding = {
        "editors": "dc:creator",
        "description": "dc:description",
        "id": "dc:identifier",
        "license": "dc:license",
        "publisher_name": "dc:publisher",
        "name": "dc:title"}
    for key, value in dataset_metadata.items():
        if key in corresponding:
            dataset.tablegroup.common_props[corresponding[key]] = value
        else:
            dataset.tablegroup.common_props['special:'+key] = value

    # Explicitly create a language table
    dataset.add_component(
        'LanguageTable')
    dataset["LanguageTable"].tableSchema.columns.append(
        Column(name="Region",
            propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#macroarea",
            datatype="string"))
    dataset["LanguageTable"].tableSchema.columns.append(
        Column(name="Family",
            propertyUrl="http://glottolog.org/glottolog/family",
            datatype="string"))
    dataset["LanguageTable"].tableSchema.columns.append(
        Column(name="Description",
            propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#description",
            datatype="string"))
    dataset["LanguageTable"].tableSchema.columns.append(
        Column(name="Comment",
            propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#comment",
            datatype="string"))

    # Explicitly create a parameter table
    dataset.add_component('ParameterTable', "English", "Indonesian", "Semantic_Field", "Elicitation_Notes", "Concepticon_ID", "Comment")

    # Explicitly create cognate table
    dataset.add_component(
        'CognateTable')

    # Create a new table for loanword properties
    dataset.add_component(
        'BorrowingTable')
    loan_table = dataset["BorrowingTable"]
    loan_table.tableSchema.columns.append(
        Column(name="Status",
            propertyUrl="http://wold.clld.org/terms#borrowed_status",
            # 1. clearly borrowed
            # 2. probably borrowed
            # 3. perhaps borrowed
            # 4. very little evidence for borrowing
            # 5. no evidence for borrowing
            # This only considers the *word form* of the item, not the morphological structure (calques, loan translations etc.)
            datatype="integer"))

    # All components have been added, ensure that all necessary ForeignKey
    # references are included. This should happen automatically, but there is a bug
    # in the implementation in pycldf 1.0.5, so do it manually.
    dataset.auto_constraints()

    # Load concept metadata
    concept_file = original.parent.joinpath("concepts.tsv").open(encoding=encoding)
    if "16" in encoding:
        bom = concept_file.read(1)
        if bom == ('\ufeff') or bom == ('\ufffe'):
            pass
        else:
            concept_file.seek(0, 0)
    ParameterTable = {}
    for l, line in enumerate(csv.DictReader(concept_file,
            delimiter="\t")):
        ParameterTable[line[concept_id]] = {
            "ID": identifier(line["English"]),
            "Name": line.get("CONCEPTICON_GLOSS") or line.get("English"),
            "English": line["English"].strip(),
            "Indonesian": line["Indonesian"].strip(),
            "Semantic_Field": line["Semantic field"],
            "Concepticon_ID": line.get("CONCEPTICON_ID"),
            "Comment": line["Concept Notes"],
            "Elicitation_Notes": ""}

    # Generate bibliography skeleton
    for metadata in original.glob("**/*.json"):
        source_data = json.load(metadata.open())
        try:
            source_id = identifier(source_data["Source"])
        except KeyError:
            source_id = identifier(metadata.stem)
            if source_id.endswith("metadata"):
                source_id = source_id[:-len("-metadata")]
            if source_id.endswith("csv") or source_id.endswith("tsv"):
                source_id = source_id[:-len(".Xsv")]
        bibitem = {}
        for key, value in source_data.items():
            if key == "Source":
                continue
            elif key == "sources":
                if len(value) == 0:
                    continue
                while len(value) > 1:
                    bi = bibitem.copy()
                    val = value.pop(-1)
                    if type(val) == dict:
                        for key, val in val.items():
                            bi[identifier(key)] = str(val)
                        dataset.sources.add(Source(genre='misc', id_=source_id+str(len(value)), **bibitem))
                    else:
                        bibitem["note"] = str(value)
                value = value[0]
                if type(value) == dict:
                    for key, value in value.items():
                        bibitem[identifier(key)] = str(value)
                else:
                    bibitem["note"] = str(value)
            else:
                bibitem[identifier(key)] = str(value)
        dataset.sources.add(Source(genre='misc', id_=source_id, **bibitem))


    # Load the original data and transform into CLDF
    FormTable = []
    CognateTable = []
    LoanTable = []
    l = 0
    unclean = {} # Dict of bad segments mapped to the forms they appeear in
    for item in original.glob("**/*.tsv"):
        file = item.open(encoding=encoding)
        if "16" in encoding:
            # Check whether there is a BOM that should not be there
            bom = file.read(1)
            if bom == ('\ufeff') or bom == ('\ufeff'):
                pass
            else:
                file.seek(0, 0)
        reader = csv.DictReader(file, delimiter="\t")
        for line in reader:
            cm = line["Comment"]
            loan = line.get("Loan", False)
            value = line["Value"]
            src = line.get("Source", item.stem)
            try:
                dataset.sources[identifier(src)]
            except ValueError:
                dataset.sources.add(Source(
                    genre='misc', id_=identifier(src), title=src))
            sources = [identifier(src)]

            for source in line.get("Reference", "").split(";"):
                if not identifier(source.strip()):
                    continue
                try:
                    src = dataset.sources[identifier(source)]
                except ValueError:
                    dataset.sources.add(Source(
                        genre='misc', id_=identifier(source), title=source))
                    src = dataset.sources[identifier(source)]
                sources.append(src.id)

            for bracket_resolution in resolve_brackets(value):
                clpa_segments = tokenize_clpa(
                    bracket_resolution, preprocess=REPLACE)
                segments = []
                for s in clpa_segments:
                    if isinstance(s, Sound):
                        segments.append(str(s))
                    else:
                        unclean.setdefault(s.origin, []).append(l)

                FormTable.append({
                    'ID': l,
                    'Language_ID': line["Language_ID"],
                    'Parameter_ID': ParameterTable[line[foreign_key]]["ID"],
                    'Form': value or '-',
                    'Segments': segments,
                    'Comment': (
                        '' if cm != cm or cm == 'nan'
                        # cm != cm is a cheap test for cm being NaN
                        else cm),
                    'Source': sources})

                alignment = line.get("Alignment", "")
                if alignment in ["#NAME?", "nan", ""]:
                    alignment = segments
                else:
                    alignment = alignment.split()
                CognateTable.append({
                    'ID': len(CognateTable),
                    'Form_ID': l,
                    'Cognateset_ID': identifier(line["Cognate Set"]),
                    'Alignment': alignment,
                    'Source': []})
                if loan:
                    LoanTable.append({
                        "ID": len(LoanTable),
                        "Status": 2,
                        "Form_ID_Target": l})

                l += 1

    # Load language metadata
    LanguageTable=[]
    for line in csv.DictReader(Path(__file__).parent.parent.joinpath("languages.tsv").open(), delimiter="\t"):
        # Merge Latitude data
        lat = line["Lat"]
        if lat:
            lat = float(lat)
        merged_lat = line.get("MergedLat")
        if merged_lat:
            merged_lat = float(merged_lat)
        if lat != merged_lat and lat and merged_lat:
            print(lat, merged_lat)
        excel_lat = line.get("ExcelLat")
        if excel_lat == "#N/A" or not excel_lat:
            excel_lat = None
        else:
            excel_lat = float(excel_lat)
        if lat != excel_lat and lat and excel_lat:
            print(lat, excel_lat)
        lat = lat or merged_lat or excel_lat

        # Merge Longitude data
        lon = line["Lon"]
        if lon:
            lon = float(lon)
        merged_lon = line.get("MergedLon")
        if merged_lon:
            merged_lon = float(merged_lon)
        if lon != merged_lon and lon and merged_lon:
            print(lon, merged_lon)
        excel_lon = line.get("ExcelLon")
        if excel_lon == "#N/A" or not excel_lon:
            excel_lon = None
        else:
            excel_lon = float(excel_lon)
        if lon != excel_lon and lon and excel_lon:
            print(lon, excel_lon)
        lon = lon or merged_lon or excel_lon

        id = line["Language ID"]
        glottolog_from_id = id.split("-")[1] if id.split("-")[0] == "p" else id.split("-")[0]
        LanguageTable.append({
            "ID": id,
            "Name": line["Language name (-dialect)"],
            "Comment": line["Comments"],
            "Description": line["Description"],
            "Glottocode": line["Glottolog"] or glottolog_from_id,
            "Family": line["Family"]})
        if lat and lon:
            LanguageTable[-1].update({
                "Latitude": lat, "Longitude": lon,
                "Region": get_region(lat, lon).address})

    # Write data back
    dataset.write(FormTable=FormTable,
                CognateTable=CognateTable,
                BorrowingTable=LoanTable,
                LanguageTable=LanguageTable,
                ParameterTable=ParameterTable.values())

    print(unclean)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cldf", type=Path, default=Path(__file__).parent.parent.joinpath("cldf"))
    parser.add_argument("datasets", type=Path, default=Path(__file__).parent.parent.joinpath("datasets"))
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--featureid", default="English=English")
    args = parser.parse_args()
    path = args.cldf
    original = args.datasets
    # Decide which column to use as key and as foreignKey
    concept_id, foreign_key = args.featureid.split("=")
    main(path, original, concept_id, foreign_key, encoding=args.encoding)

    if args.db:
        from pycldf.db import Database
        db = Database("cldf.sqlite")
        db.create(force=True)
        db.load(dataset)
