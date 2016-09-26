#!/usr/bin/env python

import os
import argparse
import json
import pandas

try:
    from nameparser import HumanName
except ImportError:
    class HumanName:
        def __init__(self, name):
            if " " in name:
                self.first = name[:name.index(" ")].strip()
                self.last = name[name.index(" "):].strip()
            else:
                self.last=name
                self.first=""

try:
    from clld.db.meta import DBSession
    from clld.db.models.common import Dataset, Contributor, ContributionContributor, ValueSet, Value
    from lexibank.models import LexibankLanguage, Concept, Provider
    model_is_available=True
except ImportError:
    raise
    class DummyDBSession:
        def add(self, data): pass
    DBSession = DummyDBSession()

    class Ignore:
        def __init__(self, *args, **kwargs): pass
    Dataset = Contributor = ContributionContributor = ValueSet = Value = Ignore
    LexibankLanguage = Concept = Provider = Ignore

    class Icon:
        name = None
    
    model_is_available=False

concepticon_path = "concepts.tsv"
def import_concepticon():
    concepticon = pandas.io.parsers.read_csv(
        concepticon_path,
        sep='\t',
        index_col="Concept ID",
        encoding='utf-16')
    concepticon["db_Object"] = [
        Concept(
            id=i,
            # GLOSS
            name=row['English'],
            semanticfield="")
        for i, row in concepticon.iterrows()]
    return concepticon

languages_path = '../lexirumah-data/languages.tsv'
def import_languages():
    # TODO: be independent of the location of lexirumah-data, but do compare with it!
    languages = pandas.io.parsers.read_csv(
        languages_path,
        sep='\t',
        index_col="Language ID",
        encoding='utf-16')
    languages["db_Object"] = [
        LexibankLanguage(
            id=i,
            name=row['Language name (-dialect)'],
            latitude=row['Lat'],
            longitude=row['Lon'])
        for i, row in languages.iterrows()]
    return languages

def report(problem, data1, data2):
    print(problem)
    print(data1)
    print("<->")
    print(data2)
    print("     [ ]")
    print()

    
copy_from_concepticon = ["English"]
copy_from_languages = ["Family", "Region", "Language name (-dialect)"]
make_sure_exists = ["Alignment", "Source"]
valuesets = {}
values = set()
def import_contribution(path, concepticon, languages, contributors={}, trust=[]):
    # look for metadata
    # look for sources
    # then loop over values
    
    mdpath = path + '-metadata.json'
    with open(mdpath) as mdfile:
        md = json.load(mdfile)

    try:
        md["abstract"]
    except KeyError:
        md["abstract"] = "[No description]"
      
    contrib = Provider(
        id=md.get("id", os.path.split(path)[-1][:-4]),
        name=md.get("name", os.path.split(path)[-1]),
        #sources=sources(md["source"]) + references(md["references"]),
        ## Provider can't take sources arguments yet.
        ## We expect "source" to stand for primary linguistic data (audio files etc.),
        ## and "references" to point to bibliographic data.
        #Provider also takes url, aboutUrl, language_count, parameter_count, lexeme_count synonym
        )
    contributor_name = HumanName(md.get("creator", "?")[0])
    contributor_id = (contributor_name.last + contributor_name.first)
    try:
        contributor = contributors[contributor_id]
    except KeyError:
        contributors[contributor_id] = contributor = Contributor(
            id=contributor_id,
            name=str(contributor_name))
    DBSession.add(ContributionContributor(contribution=contrib, contributor=contributor))

    if mdpath not in trust:
        with open(mdpath, "w") as mdfile:
            json.dump(md, mdfile, indent=2)

    data = pandas.io.parsers.read_csv(
            path,
            sep="," if path.endswith(".csv") else "\t",
            encoding='utf-16')

    for column in make_sure_exists+copy_from_concepticon+copy_from_languages:
        if column not in data.columns:
            data[column] = ""
        data[column] = data[column].astype(str)

    for i, row in data.iterrows():
        language = row["Language_ID"]
        if pandas.isnull(language):
            report(
                "No language given!",
                (language),
                None)
            del data[i]
            continue
        for column in copy_from_languages:
            if row[column] != languages[column][language]:
                data.set_value(i, column, languages[column][language])
                
        feature = row["Feature_ID"]
        if pandas.isnull(feature):
            en = pandas.isnull(row["English"])
            if pandas.isnull(en) or en not in concepticon["English"]:
                report(
                    "Feature not set, and unable to reconstruct",
                    feature,
                    en)
            else:
                feature = (concepticon["English"] == en).argmax
        for column in copy_from_concepticon:
            if row[column] != concepticon[column][feature]:
                data.set_value(i, column, concepticon[column][feature])
                
        value = row["Value"]
        if pandas.isnull(value):
            alignment = row["Alignment"]
            if pandas.isnull(alignment):
                report("Value not given, and unable to reconstruct",
                       value,
                       alignment)
            else:
                value = "".join(alignment.split())
                
        if feature in valuesets:
            vs = valuesets[feature]
        else:
            vs = valuesets[feature] = ValueSet(
                id="{:s}-{:s}".format(language, feature),
                parameter=concepticon["db_Object"][feature],
                language=languages["db_Object"][language],
                contribution=contrib,
                source=row['Source'])
        vid = "{:s}-{:s}-{:}".format(language, feature, value)
        if vid not in values:
            DBSession.add(
                Value(
                    id=vid,
                    valueset=vs,
                    name=value))
            values.add(vid)

    if path not in trust:
        data.sort_values(by=["Feature_ID", "Family", "Region"], inplace=True)
        data = data[[
            "Feature_ID",
            "English",
            "Language_ID",
            "Language name (-dialect)",
            "Family",
            "Region",
            "Value"]]
        data.to_csv(
            path,
            index=False,
            sep="," if path.endswith(".csv") else "\t",
            encoding='utf-16')
    return data


def import_cldf(srcdir, concepticon, languages, trust=[]):
    # loop over values
    # check if language needs to be inserted
    # check if feature needs to be inserted
    # add value if in domain
    datasets = {}
    for dirpath, dnames, fnames in os.walk(srcdir):
        for fname in fnames:
            if os.path.splitext(fname)[1] in ['.tsv', '.csv']:
                print("Importing {:s}…".format(os.path.join(dirpath, fname)))
                datasets[os.path.join(dirpath, fname)] = import_contribution(
                    os.path.join(dirpath, fname),
                    concepticon,
                    languages,
                    trust=trust)
                print("Import done.")
    return datasets


def main(trust=[languages_path, concepticon_path]):
    with open("metadata.json") as md:
        dataset_metadata = json.load(md)
    DBSession.add(
        Dataset(
            id=dataset_metadata["id"],
            name=dataset_metadata["name"],
            publisher_name=dataset_metadata["publisher_name"],
            publisher_place=dataset_metadata["publisher_place"],
            publisher_url=dataset_metadata["publisher_url"],
            license=dataset_metadata["license"],
            domain=dataset_metadata["domain"],
            contact=dataset_metadata["contact"],
            jsondata={
                'license_icon': dataset_metadata["license_icon"],
                'license_name': dataset_metadata["license_name"]}))

    concepticon = import_concepticon()
    languages = import_languages()
    import_cldf("datasets", concepticon, languages, trust=trust)
    if languages_path not in trust:
        languages.to_csv(
            languages_path,
            sep='\t',
            encoding='utf-16')
    if concepticon_path not in trust:
        concepticon.to_csv(
            concepticon_path,
            sep='\t',
            encoding='utf-16')

import sys
sys.argv=["i", "../lexibank/development.ini"]

if model_is_available:
        from clld.scripts.util import initializedb
        from clld.db.util import compute_language_sources
        try:
            initializedb(create=main, prime_cache=lambda x: None)
        except SystemExit:
            print("done")
else:
        parser = argparse.ArgumentParser(description="Process LexiRumah data with consistency in mind")
        parser.add_argument("--sqlite", default=None, const="gramrumah.sqlite", nargs="?",
                            help="Generate an sqlite database from the data")
        parser.add_argument("--trust", "-t", nargs="*", type=argparse.FileType("r"), default=[],
                            help="Data files to be trusted in case of mismatch")
        #args = parser.parse_args()
        #main([x.name for x in args.trust])
        main([languages_path, concepticon_path])
