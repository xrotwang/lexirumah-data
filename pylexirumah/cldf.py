import re
import math

import csv
import json

import sys
import argparse

from clldutils.path import Path
from pycldf.sources import Source
from pycldf.dataset import Wordlist
from clldutils.csvw.datatypes import integer
from clldutils.csvw.metadata import Column, Table, Schema, ForeignKey

from segment import tokenize_word_reversibly


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

dataset = Wordlist.from_metadata(path)


def identifier(string):
    return re.sub('(\W|^(?=\d))+','_', string).strip("_")


# Explicitly create a language table
dataset.add_component(
    'LanguageTable',
    Column(name="Glottocode",
           propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#glottocode",
           valueUrl="http://glottolog.org/resource/languoid/id/{ID}",
           required=True))
dataset["LanguageTable"].tableSchema.columns.append(
    Column(name="Family",
           propertyUrl="http://glottolog.org/glottolog/family"))
dataset["LanguageTable"].tableSchema.columns.append(
    Column(name="Description"))
dataset["LanguageTable"].tableSchema.columns.append(
    Column(name="Comment"))

# Explicitly create a parameter table
dataset.add_component('ParameterTable', "English", "Indonesian", "Semantic_Field", "Elicitation_Notes", "Concepticon_ID", "Comment")

# Explicitly create cognate table
dataset.add_component(
    'CognateTable')
dataset["CognateTable"].tableSchema.columns.append(
    Column(name="ID",
           required=True,
           datatype="integer"))

# Create a new table for loanword properties
loan_table = Table(common_props={
    "dc:conformsTo": "http://cldf.clld.org/v1.0/terms.rdf#ValueTable",
    "dc:conformsTo-is-a-lie": True},
                   url="loans.csv",
                   parent=dataset.tablegroup)
loan_table.tableSchema.columns.append(
    Column(name="Form_ID",
           required=True,
           datatype="integer"))
loan_table.tableSchema.foreignKeys.append(
    ForeignKey.fromdict({
        "reference": {
            "resource": "forms.csv",
            "columnReference": ["ID"]},
        "columnReference": ["Form_ID"]}))
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
dataset.tables.append(loan_table)


# Load concept metadata
concept_file = original.parent.joinpath("concepts.tsv").open(encoding=args.encoding)
if "16" in args.encoding:
    bom = concept_file.read(1)
    if bom == ('\ufeff') or bom == ('\ufeff'):
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

# Load the original data and transform into CLDF
FormTable = []
CognateTable = []
LoanTable = []
additional_sources = {}
l = 0
for item in original.iterdir():
    if item.suffix == ".tsv":
        source_id = ''.join(item.stem.split())
        try:
            metadata = item.parent.joinpath(item.name+"-metadata.json")
            source_data = json.load(metadata.open())
            bib = {}
            for key in source_data:
                bib[identifier(key)] = str(source_data[key])
            dataset.sources.add(Source(genre='misc', id_=source_id, **bib))
        except FileNotFoundError:
            pass

        file = item.open(encoding=args.encoding)
        if "16" in args.encoding:
            # Check whether there is a BOM that should not be there
            bom = file.read(1)
            if bom == ('\ufeff') or bom == ('\ufeff'):
                pass
            else:
                file.seek(0, 0)
        reader = csv.DictReader(file, delimiter="\t")
        for line in reader:
            cm = line["Comment"]
            loan = line["Loan"]
            value = line["Value"]
            if line["Reference"]:
                name = identifier(line["Reference"])
                if name:
                    additional_sources[name] = {}
                    source = [name]
                else:
                    source = []
            else:
                source = []

            FormTable.append({
                'ID': l,
                'Language_ID': line["Language_ID"],
                'Parameter_ID': ParameterTable[line[foreign_key]]["ID"],
                'Value': value or '-',
                'Segments': tokenize_word_reversibly(value, clean=True),
                'Comment': (
                    '' if cm != cm or cm == 'nan'
                    # cm != cm is a cheap test for cm being NaN
                    else cm),
                'Source': [source_id] + source})
            CognateTable.append({
                'ID': len(CognateTable),
                'Form_ID': l,
                'Cognate_set_ID': identifier(line["Cognate Set"]),
                'Alignment': line.get("Alignment", "").split(" "),
                'Cognate_source': [],
                'Alignment_source': []})
            if line["Loan"]:
                LoanTable.append({
                    "Status": 2,
                    "Form_ID": l})
            l += 1
        for source_id, bib in additional_sources.items():
            dataset.sources.add(Source(genre='misc', id_=source_id, **bib))

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
        "Latitude": lat,
        "Longitude": lon,
        "Comment": line["Comments"],
        "Description": line["Description"],
        "Glottocode": line["Glottolog"] or glottolog_from_id,
        "Family": line["Family"]})

# Write data back
dataset.write(FormTable=FormTable,
              CognateTable=CognateTable,
              ValueTable=LoanTable,
              LanguageTable=LanguageTable,
              ParameterTable=ParameterTable.values())

