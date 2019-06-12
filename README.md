# lexiruma-data

The data underlying the [LexiRumah](http://lexirumah.model-ling.eu/lexirumah/)
[CLLD](http://clld.org) database is maintained and edited here, as well as the
[`pylexirumah`](#pylexirumah) python package, which provides an API for
accessing, manipulating and publishing the database content.

## CLDF

The `cldf` directory contains the dataset in
[CLDF 1.0 Wordlist](https://github.com/glottobank/cldf/tree/master/modules/Wordlist)
format. Included beyond forms, which are cross-linked to lects (with [Glottolog](http://glottolog.org) IDs)
and concepts (with [Concepticon](http://concepticon.clld.org) references), are
cognate judgements (automatically coded for the time being, but manual changes will
be documented) and a borrowing table.

## Non-CLDF

In addition to the CLDF dataset, we retain data which has not (yet) been merged into
the dataset. The `noncldf` folder contains the sociolinguistic profile of many of
the speakers who contributed word lists as informants.

The `keraf` subfolder
contains the original digitizations of the word lists from Keraf (1978) for
reference. The forms in the cldf may have been normalized to IPA and some
concepts have been merged with close-but-not-perfect synonyms.

The `sulawesi` subfolder contains wordlists from South-East Sulawesi, provided by
David Mead, as well as the draft for a script to import these lects into LexiRumah.

## `pylexirumah`
[![Build Status](https://travis-ci.org/lessersunda/lexirumah-data.svg?branch=with_lexi_data)](https://travis-ci.org/lessersunda/lexirumah-data)

### `tests`
The `tests` directory contains tests for functionality in `pylexirumah`.
