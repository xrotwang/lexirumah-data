import math

import csv
import json

from clldutils.path import Path
from pycldf.sources import Source
from pycldf.dataset import Wordlist
from clldutils.csvw.datatypes import integer
from clldutils.csvw.metadata import Column, Table, Schema, ForeignKey

from segment import tokenize_word_reversibly

dataset = Wordlist.in_dir(Path(__file__).parent.parent.joinpath("cldf"))

# Add cognate set and alignment columns to forms table
forms_table = dataset.tables[0]
forms_table.tableSchema.columns.append(
    Column(name="Cognate_Set",
           propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#cognateSet"))
forms_table.tableSchema.columns.append(
    Column(name="Alignment",
           propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#alignment",
           separator=" "))

# Explicitly create a language table
dataset.add_component('LanguageTable', "Glottocode")
dataset["LanguageTable"].tableSchema.columns[-1].propertyUrl = "http://cldf.clld.org/v1.0/terms.rdf#glottocode"
dataset["LanguageTable"].tableSchema.columns[-1].valueUrl = "http://glottolog.org/resource/languoid/id/{ID}"
dataset["LanguageTable"].tableSchema.columns[-1].required = True
dataset["LanguageTable"].tableSchema.columns.append(
    Column(name="Family",
           propertyUrl="http://glottolog.org/glottolog/family"))
dataset["LanguageTable"].tableSchema.columns.append(
    Column(name="Description"))
dataset["LanguageTable"].tableSchema.columns.append(
    Column(name="Comment"))

# Explicitly create a parameter table
dataset.add_component('ParameterTable', "English", "Indonesian", "Semantic_Field", "Elicitation_Notes", "Concepticon_ID", "Comment")
 
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
ParameterTable = {}
for l, line in enumerate(csv.DictReader(
        Path(__file__).parent.parent.joinpath("concepts.tsv").open(),
        delimiter="\t")):
    ParameterTable[line["English"]] = {
        "ID": l,
        "Name": line["CONCEPTICON_GLOSS"],
        "English": line["English"].strip(),
        "Indonesian": line["Indonesian"].strip(),
        "Semantic_Field": line["Semantic field"],
        "Concepticon_ID": line["CONCEPTICON_ID"],
        "Comment": line["Concept Notes"],
        "Elicitation_Notes": ""}

# Load the original data and transform into CLDF (concepts and languages still missing)
FormTable = []
LoanTable = []
additional_sources = {}
l = 0
for item in Path(__file__).parent.parent.joinpath("datasets").iterdir():
    if item.suffix == ".tsv":
        source_id = ''.join(item.stem.split())
        try:
            metadata = item.parent.joinpath(item.name+"-metadata.json")
            source_data = json.load(metadata.open())
            bib = {}
            for key in source_data:
                bib[key.replace(" ", "").replace(":", "")] = str(source_data[key])
            dataset.sources.add(Source(genre='misc', id_=source_id, **bib))
        except FileNotFoundError:
            pass

        reader = csv.DictReader(item.open(), delimiter="\t")
        for line in reader:
            cm = line["Comment"]
            loan = line["Loan"]
            value = line["Value"]
            if line["Reference"]:
                name = line["Reference"].replace(";", "").replace(" ", "_").replace("?", "XXX")
                additional_sources[name] = {}
                source = [name]
            else:
                source = []
            FormTable.append({
                'ID': l,
                'Language_ID': line["Language_ID"],
                'Parameter_ID': ParameterTable[line["English"]]["ID"],
                'Value': value,
                'Segments': tokenize_word_reversibly(value, clean=True),
                'Comment': (
                    '' if cm != cm or cm == 'nan'
                    # cm != cm is a cheap test for cm being NaN
                    else cm),
                'Source': [source_id] + source,
                'Cognate_Set': line["Cognate Set"],
                'Alignment': line["Alignment"].split(" ")})
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
              ValueTable=LoanTable,
              LanguageTable=LanguageTable,
              ParameterTable=ParameterTable.values())

