#!/usr/bin/env python
from __future__ import unicode_literals, division

from clld_glottologfamily_plugin.util import load_families
from pyconcepticon.api import Concepticon

import pandas
import json
import os
import sys

class DatabaseInconsistency(BaseException):
    """ An inconsistency was found in the data repository """
    
def warn(incopatibility):
    sys.stdout.write(incopatibility)
    sys.stdout.write("\n")

def error(incompatibility):
    raise DatabaseInconsistency(incompatibility)

def fix_first(incompatibility):
    yield warn(incompatibility)
    yield error(incompatibility)

def load_metadata(path):
    mdpath = path + '-metadata.json'
    if not os.path.exists(mdpath):
        on_error("Metadata file for {:s} ({:s}) does not exist!".format(path, mdpath))
    with open(mdpath) as mdfile:
        try:
            md = json.load(mdfile)
        except json.decoder.JSONDecodeError:
            on_error("Metadata file was not valid json!")
    return md

def cldf2clld(source, contrib, id_):
    name = source.id
    if source.get('author'):
        name = source['author']
    if source.get('year'):
        name += ' %s' % source['year']
    description = source.get('title')
    return LexibankSource(
        id=unique_id(contrib, id_),
        provider=contrib,
        bibtex_type=getattr(EntryType, source.genre, EntryType.misc),
        name=name,
        description=description,
        **{k: v for k, v in source.items() if k in FIELDS})

def equal(true_value, other_value):
    if true_value!=other_value:
        on_error("{:} did not match {:}…")
        other_value = true_value
        
def check_dataset(path, languoids, conceptsets):
    data = pandas.io.parsers.read_csv(
        path,
        sep="," if path.endswith(".csv") else "\t",
        encoding='utf-16')
    if data.empty:
        on_error("Data file is empty!")
    if 'Language' not in data:
        data['Language'] = None
    if 'Family' not in data:
        data['Family'] = None
    if 'Region' not in data:
        data['Region'] = None
    if 'English' not in data:
        data['English'] = None
    for i, row in data.iterrows():
        try:
            fid = row['Feature_ID']
        except KeyError:
            on_error("Data file has no column Feature_ID!")
            fid = None

        try:
            lang_id = row['Language_ID']
        except KeyError:
            on_error("Data file has no column Language_ID!")

        try:
            gid = (lang_id.split("-")[1]
                   if lang_id.split("-")[0] == "p" else
                   lang_id.split("-")[0])
        except TypeError:
            on_error("Language_ID is not specified for {:}!".format(row))

        try:
            language = languoids.loc[lang_id]
        except KeyError:
            on_error("Language_ID {:s} not reflected in language list!".format(lang_id))
        if language["Language name (-dialect)"] != row.get("Language"):
            on_error("Language name {:} did not match expected {:s}".format(
                row.get("Language"), language["Language name (-dialect)"]))
            data["Language"][i] = language["Language name (-dialect)"]
            data["Family"][i] = language["Family"]
            data["Region"][i] = language["Region"]

        try:
            concept = conceptsets.loc[fid]
        except KeyError:
            on_error("Feature_ID {:s} not reflected in concept list!".format(fid))
        if concept["English"] != row.get("English"):
            on_error("English meaning {:} did not match expected {:s}".format(
                row.get("English"), concept["English"]))
            data["English"][i] = concept["English"]

        try:
            counterpart = row['Value']
        except KeyError:
            on_error("Data file has no Value column for the counterparts!")

        try:
            align = data['Alignment']
        except KeyError:
            on_error("There was no alignment column…")
            data['Alignment'] = [
                None if pandas.isnull(x) else " ".join(x)
                for x in data['Value']]

        try:
            cogn = data['Cognatesets']
        except KeyError:
            on_error("There was no cognate set column…")
            data["Cognatesets"] = None

        try:
            loan = data['Loan']
        except KeyError:
            on_error("There was no loan column…")
            data["Loan"] = None

    columns = list(data.columns)
    fixed_order = ["Feature_ID", "Language_ID", "Language", "English", "Value", "Alignment", "Cognatesets"]
    for c in fixed_order:
        columns.remove(c)
    data = data[fixed_order + columns]
    data["Family"]
    print(data.to_string())
    if on_error == warn:
        on_error("Writing minor changes back to file")
        data.to_csv(
            path,
            index=False,
            sep="," if path.endswith(".csv") else "\t",
            encoding='utf-16')
    return data


def check_cldf(srcdir, conceptsets, languoids):
    all_data = pandas.DataFrame()
    for dirpath, dnames, fnames in os.walk(srcdir):
        for fname in fnames:
            print("CHECKING DATASET {:s}".format(fname))
            if os.path.splitext(fname)[1] in ['.tsv', '.csv']:
                md = load_metadata(os.path.join(dirpath, fname))
                try:
                    md.pop('dc:title')
                    md.pop('dc:bibliographicCitation')
                    md.pop('dc:identifier')
                    md.pop('dc:license')
                    md.pop('aboutUrl')
                except KeyError as k:
                    on_error("Metadata file missing key: {:s}!".format(
                        k.args[0]))
                if md:
                    on_error("Metadata contained unused entries: {:}!".format(
                        md))

                try:
                    content = pandas.io.parsers.read_csv(
                        os.path.join(dirpath, fname),
                        sep="," if fname.endswith(".csv") else "\t",
                        encoding='utf-8')
                    on_error("Data file was utf-8 encoded…")
                    content.to_csv(
                        os.path.join(dirpath, fname),
                        index=False,
                        sep="," if fname.endswith(".csv") else "\t",
                        encoding='utf-16')
                except UnicodeDecodeError:
                    # Assume the data was in utf-16 already
                    pass
                try:
                    data = check_dataset(os.path.join(dirpath, fname), languoids, conceptsets)
                except pandas.io.common.EmptyDataError:
                    on_error("Data file is empty!")
                except pandas.io.common.CParserError:
                    on_error("Data file was not clean *sv!")

                data["Source"] = os.path.join(dirpath, fname)
                all_data = pandas.concat((all_data, data))
    print("ALL DATA IS THUS")
    all_data.sort_values(by=["Feature_ID", "Family", "Region", "Language"], inplace=True)
    print(all_data.to_string())
    return all_data
                    

def main():
    datadir = "./"
    LEXIBANK_REPOS = os.path.join(datadir, "lexibank")
    
    try:
        dataset = json.load(open(os.path.join(LEXIBANK_REPOS, "metadata.json")))
        print("DATASET METADATA")
    except FileNotFoundError:
        on_error("Database metadata file (lexibank/metadata.json) unavailable!")
    except json.decoder.JSONDecodeError:
        on_error("Database metadata file was not valid json!")
    try:
        print(dataset["id"], 
              dataset["name"],
              dataset["publisher_name"],
              dataset["publisher_place"],
              dataset["publisher_url"],
              dataset["license"],
              dataset["license_icon"],
              dataset["license_name"],
              dataset["domain"],
              dataset["contact"],
              sep="\n")
    except KeyError as k:
        on_error("Database metadata file missing key: {:s}!".format(
            k.args[0]))
    
    concept_path = os.path.join(LEXIBANK_REPOS, "concepts.tsv")
    try:
        try:
            concepts = pandas.io.parsers.read_csv(concept_path,
                                                index_col="Concept ID", sep="\t", encoding="utf-16")
        except FileNotFoundError:
            on_error("Concept list file (lexibank/concepts.tsv) not found!")
        except pandas.io.common.EmptyDataError:
            on_error("Concept list file was empty!")
        except pandas.io.common.CParserError:
            concepts = pandas.io.parsers.read_csv(concept_path,
                                                    index_col="Concept ID", sep="\t", encoding="utf-8")
            on_error("Concept list file was utf-8 encoded…")
            concepts.to_csv(concept_path, sep="\t", index_label="Concept ID", encoding="utf-16")
        except:
            raise
    except TypeError:
        on_error("Concept list file may have been empty!")
    except ValueError:
        on_error("Concept list has no column 'Concept ID'!")
        
    # FIXME: Compare concepts to concepticon
    concepticon = Concepticon("/home/gereon/databases/virtualenv/lib/python3.5/site-packages/pyconcepticon-0.1-py3.5.egg/concepticondata/")
    
    language_path = os.path.join(datadir, "languages.tsv")
    try:
        try:
            languages = pandas.io.parsers.read_csv(language_path,
                                                index_col="Language ID", sep="\t", encoding="utf-16")
        except FileNotFoundError:
            on_error("Language list file (lexibank/languages.tsv) not found!")
        except pandas.io.common.EmptyDataError:
            on_error("Language list file was empty!")
        except pandas.io.common.CParserError:
            languages = pandas.io.parsers.read_csv(language_path,
                                                    index_col="Language ID", sep="\t", encoding="utf-8")
            on_error("Language list file was utf-8 encoded…")
            languages.to_csv(language_path, sep="\t", index_label="Language ID", encoding="utf-16")
        except:
            raise
    except TypeError:
        on_error("Language list file may have been empty!")
    except ValueError:
        on_error("Language list has no column 'Language ID'!")

    return check_cldf(os.path.join(LEXIBANK_REPOS, "datasets"), concepts, languages)

    # Check language families

if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1] == "fix":
        on_error = warn
    elif len(sys.argv)>1 and sys.argv[1] == "fix_first":
        on_error = fix_first
    else:
        on_error = error
    all_data = main()
    if on_error == warn:
        warn("Creating new all_data.tsv…")
        all_data.to_csv(
            "all_data.tsv",
            index=False,
            sep="\t",
            encoding='utf-16')
