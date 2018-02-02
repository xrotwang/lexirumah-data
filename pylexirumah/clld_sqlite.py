#!/usr/bin/env python

"""Process all lexirumah data into a database.

Take all the data and metadata in `datasets/`, and if possible
generate a lexirumah sqlite from it.

"""

import re
import math

import os
import argparse
import json
import pandas
import sys

import pycldf

import lexibank
import transaction

from clld.scripts.util import parsed_args
from clld.lib.bibtex import EntryType
from lexibank.scripts.initializedb import prime_cache

from util import identifier


# Attempt to load enoug Lexirumah to construct an SQLite database for it.
from clld.db.meta import DBSession
from clld.db.models import common
Dataset = common.Dataset
Editor = common.Editor
Contributor = common.Contributor
ContributionContributor = common.ContributionContributor
ValueSet = common.ValueSet
Identifier = common.Identifier
LanguageIdentifier = common.LanguageIdentifier
from lexibank.models import (
    LexibankLanguage, LexibankSource, Concept, Provider, Counterpart,
    CognatesetCounterpart, Cognateset, CognatesetCounterpartReference,
    CounterpartReference)
from clld_glottologfamily_plugin.models import Family
model_is_available = True


ICONS = iter(
    ['c0000dd',
     'fdd0000'])


# Utility functions
def report(problem, *args, process_log=None):
    """Write a problem report to a log file.

    There is probably a `logging` module that does this better.

    """
    process_log = open(process_log, 'a') if process_log else sys.stdout
    process_log.write(problem)
    for arg in args:
        process_log.write("\n  ")
        process_log.write(arg)
    process_log.write("\n")


# Define some paths.
concepticon_path = "concepts.tsv"
languages_path = "languages.tsv"
process_log = None


def import_concepticon(wordlist):
    """Load parameter (concept) data from CLDF wordlist

    Load the concepts from the pycldf word list passed as argument, and put the
    corresponding Concept objects in the database.

    """
    concepticon = {}
    for row in wordlist["ParameterTable"].iterdicts():
        id = row["ID"]
        concepticon_id = row.get('Concepticon_ID')
        if concepticon_id in ["0", "None", "???"]:
            concepticon_id = ""
        concepticon[id] = Concept(
            id=id,
            name=row["English"],
            indonesian=row["Indonesian"],
            semanticfield=row.get("Semantic_Field"),
            elicitationnotes=row["Elicitation_Notes"],
            origin=("Core set" if identifier(row["Core_Set"] or '')=='core_set'
                    else ("Keraf" if "Keraf" in (row["Comment"] or '') or "Keraf" in (row["Core_Set"] or '')
                          else "Extended")),
            concepticon_id=concepticon_id,
            comment=row["Comment"] or '',
            )
    return concepticon


def create_language_object(row, families={}, identifiers={}):
    """Create a new Language object from a CLDF LanguageTable row.

    Also create its Family if necessary.

    """
    language = row["ID"]

    family = row["Family"]
    if family not in families:
        print("Creating object for language family", family)
        families[family] = Family(
            id=family.lower(),
            jsondata={"icon": next(ICONS)},
            name=family)

    l = LexibankLanguage(
        id=row["ID"],
        name=row['Name'],
        family=families[family],
        region=row.get("Region", row.get("Macroarea")),
        latitude=row['Latitude'],
        longitude=row['Longitude'],
        description=row['Description'],
        comment=row['Comment'],
        culture=row['Culture'],
    )

    if row["Iso"]:
        iso_code = row["Iso"]
        if iso_code in identifiers:
            DBSession.add(LanguageIdentifier(
                language=l, identifier=identifiers[iso_code]))
        else:
            identifiers[iso_code] = iso = Identifier(
                id=iso_code, name=iso_code, type='iso639-3')
            DBSession.add(LanguageIdentifier(
                language=l, identifier=iso))

    if language.startswith("p-"):
        glottolog_code = language.split("-")[1]
        if glottolog_code in identifiers:
            glottolog = identifiers[glottolog_code]
        else:
            glottolog = identifiers[glottolog_code] = Identifier(
                id=glottolog_code, name=glottolog_code,
                type='glottolog')
        DBSession.add(LanguageIdentifier(
            language=l, identifier=glottolog))
    else:
        glottolog_code = language.split("-")
        if glottolog_code[0] in identifiers:
            glottolog = identifiers[glottolog_code[0]]
        else:
            glottolog = identifiers[glottolog_code[0]] = Identifier(
                id=glottolog_code[0], name=glottolog_code[0],
                type='glottolog')
        DBSession.add(LanguageIdentifier(
            language=l, identifier=glottolog,
            description=("is" if len(glottolog_code) == 1 else
                         "is dialect of")))

    return l


def import_languages(wordlist):
    """Load language metadata from languages tsv.

    Load the Lects from the pycldf word list passed as argument, and put the
    corresponding LexibankLanguage objects in the database.

    """
    lects = {}
    for row in wordlist["LanguageTable"].iterdicts():
        id = row["ID"]
        lects[id] = create_language_object(row)
    return lects


def import_sources(wordlist, contribution, contributors = {}):
    """Load the bibliography

    """
    contributions = {}
    by_name = {}
    for source in wordlist.sources.items():
        fields = source.entry.fields

        # Generate a citation from the source
        citation_contrib = None
        for role, people in source.entry.persons.items():
            if not people:
                continue
            names = " and ".join(map(str, people))
            fields[role] = names

            if not citation_contrib:
                if len(people) == 1:
                    citation_contrib = " ".join(people[0].last())
                elif len(people) == 2:
                    citation_contrib = "{:} & {:}".format(" ".join(people[0].last()),
                                                          " ".join(people[1].last()))
                else:
                    citation_contrib = "{:} et al.".format(" ".join(people[0].last()))

        if citation_contrib:
            if fields.get("year"):
                name = "{:}, {:}".format(citation_contrib, fields["year"])
            else:
                name = "{:}".format(citation_contrib)
        else:
            title_like = fields.get("title") or fields.get("note")
            if fields.get("year"):
                name = "{:}, {:}".format(title_like, fields["year"])
            else:
                name = "{:}".format(title_like)
        if name in by_name:
            name = "{:}a".format(name)
        while name in by_name:
            name = name[:-1]+chr(ord(name[-1]) + 1)

        # create a contribution
        contrib = LexibankSource(
            id=source.id,
            name=name,
            bibtex_type=vars(EntryType).get(source.genre) or EntryType.misc,
            provider=contribution)
        for key, value in fields.items():
            if hasattr(contrib, key) and not getattr(contrib, key):
                setattr(contrib, key, value)
            else:
                contrib.jsondata[key] = value

        DBSession.add(contrib)
        contributions[source.id] = contrib
        by_name[name] = contrib

    return contributions


def import_forms(
        wordlist,
        concepticon,
        languages,
        bibliography,
        contribution,
        trust=[],
        valuesets={},
        values={},
        cognatesets={},
        COGNATESETS_CONTRIB=None):
    """Load a word list from a file.

    Import a contribution (tsv dataset and its metadata file)
    corresponding to one word list (may contain several languages)
    from `path`.

    `trust` is a list of filenames we have to assume to be correct,
    and are not permitted to write back to.  All other files may be
    updated.

    """

    # Import all the rows.
    loans = {}
    for loan in wordlist["BorrowingTable"].iterdicts():
        if loan["Status"] > loans.get("Form_ID_Target", 0):
            loans[loan["Form_ID_Target"]] = loan
    forms = {}
    for row in wordlist["FormTable"].iterdicts():
            language = languages[row["Lect_ID"]]
            feature = concepticon[row["Concept_ID"]]
            sources = [bibliography[s] for s in row["Source"]]

            # Create the objects representing the form in the
            # database. This is a value in a value set.
            value = row["Form"]

            vsid = identifier("{:s}-{:}".format(language.id, feature.id))
            try:
                vs = valuesets[vsid]
            except KeyError:
                vs = valuesets[vsid] = ValueSet(
                    vsid,
                    parameter=feature,
                    language=language,
                    contribution=contribution)
            vid = row["ID"]
            form = Counterpart(
                id=vid,
                valueset=vs,
                loan=loans.get(row["ID"], {'Status': 0})['Status'],
                comment=row['Comment'],
                name=value,
                segments=" ".join(row["Segments"]))
            for source in sources:
                DBSession.add(CounterpartReference(
                    counterpart=form,
                    source=source))
            forms[vid] = form
            DBSession.add(form)
    return forms


def import_cognatesets(dataset, forms, bibliography, contribution, cognatesets={}):
    cognateset_by_formid = {}
    for row in dataset["CognateTable"].iterdicts():
        # Only incorporate the newest cognate codings.
        cognateset_by_formid[row["Form_ID"]] = row
    for row in cognateset_by_formid.values():
        cognateset_id = row["Cognateset_ID"]
        try:
            cognateset = cognatesets[cognateset_id]
            cognateset.name = forms[row["Form_ID"]].name
        except KeyError:
            cognateset = cognatesets[cognateset_id] = Cognateset(
                id=row["Cognateset_ID"],
                contribution=contribution,
                name=forms[row["Form_ID"]].name)
        assoc = (
            CognatesetCounterpart(
                cognateset=cognateset,
                doubt=True if "LexStat" in row["Source"] else False,
                alignment=" ".join(row["Alignment"]),
                counterpart=forms[row["Form_ID"]]))
        for source in row["Source"]:
            DBSession.add(CognatesetCounterpartReference(
                cognatesetcounterpart=assoc,
                source=bibliography[source]))


def db_main():
    """Build the database.

    Load the CLDF dataset and turn it into a SQLite dataset.
    """
    dataset = pycldf.Wordlist.from_metadata("Wordlist-metadata.json")

    g = dataset.properties.get

    ds = Dataset(
        id=g("dc:identifier", identifier(g("dc:title", "Wordlist"))),
        name=g("dc:title", g("dc:identifier", "Wordlist").title()),
        publisher_name=g("dc:publisher", None),
        # publisher_place=dataset_metadata["publisher_place"],
        # publisher_url=dataset_metadata["publisher_url"],
        license=g("dc:license", None),
        domain=g("clld:domain", "localhost"),
        contact=g("clld:contact"),
        jsondata={
            "license_icon": "cc-by.png",
            "license_name": "Creative Commons Attribution 4.0 International License"})
    DBSession.add(ds)

    provider = Provider(
        id=ds.id,
        name=ds.name,
        description=g("dc:description"),
        license=g("dc:license"),
        jsondata={},
        url="")

    contributors = {}
    primary = True
    for i, editor in enumerate(g("dc:creator", [])):
        # Primary and secondary editors are in the same list,
        # separated by a not-value.
        if not editor:
            primary = False
            continue

        contributor_id = identifier(editor)
        # FIXME: Don't use ID hack, instead hand contributors dict
        # through.
        try:
            contributor = contributors[contributor_id]
        except KeyError:
            contributors[contributor_id] = contributor = Contributor(
                id=contributor_id,
                name=editor)
        DBSession.add(Editor(dataset=ds, contributor=contributor,
                             ord=i, primary=primary))

    concepticon = import_concepticon(dataset)
    languages = import_languages(dataset)
    sources = import_sources(dataset, contribution=provider)
    forms = import_forms(dataset, concepticon, languages, sources, contribution=provider)
    cognatesets = import_cognatesets(dataset, forms, sources, contribution=provider)


def main():
    """Construct a new database from scratch."""
    args = parsed_args(
        args=[os.path.join(
                  os.path.dirname(os.path.dirname(lexibank.__file__)),
                  "development.ini")])

    with transaction.manager:
        db_main()
    with transaction.manager:
        prime_cache(args)


if __name__ == '__main__':
    main()
