#!/usr/bin/env python

"""Create glottolog-style ini files for each lect in our (pre-1.0!) CLDF language table."""

import pandas
import configparser

languages = pandas.read_csv("languages.tsv", sep="\t")

for i, row in languages.iterrows():
    if row["Language ID"].startswith("p-"):
        continue
    with open("{:}.ini".format(row["Language ID"]), "w") as inifile:
        inicontent = configparser.ConfigParser()
        inicontent.add_section('core')
        inicontent.set('core', 'name', row["Language name (-dialect)"])
        inicontent.set('core', 'glottocode', row["Language ID"])
        inicontent.set('core', 'level', 'dialect')
        if not pandas.isnull(row["ISO_code"]):
            inicontent.set('core', 'iso639-3', row["ISO_code"])
        if not pandas.isnull(row["Lat"]):
            inicontent.set('core', 'latitude', "{:f}".format(row["Lat"]))
            inicontent.set('core', 'longitude', "{:f}".format(row["Lon"]))
        inicontent.set('core', 'macroareas', "Papunesia")
        inicontent.set('core', 'countries', "Indonesia (ID)")
        inicontent.add_section('sources')
        inicontent.set('sources', 'glottolog', "...")
        inicontent.add_section('altnames')
        inicontent.set('altnames', 'lexirumah', row["Language ID"])
        inicontent.add_section('additional_info')
        if not pandas.isnull(row["Comments"]):
            inicontent.set('additional_info', 'sunda_comment', row["Comments"])
        
        inicontent.write(inifile)

