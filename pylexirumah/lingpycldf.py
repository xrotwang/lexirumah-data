#!/usr/bin/env python

"""Convert between LingPy and CLDF (pre-1.0 or Wordlist) formats

Example
-------
    $ python pylexirumah/lingpycldf.py cldf cldf/Wordlist-metadata.json edictor.tsv
"""

import sys

import csv
import collections

import pycldf.dataset
from clldutils.clilib import ArgumentParser


def cldf_to_lingpy(columns, replacement=None):
    """Turn CLDF column headers into LingPy column headers.

    Parameters
    ----------
    columns : str or list of str
        This is either a single CLDF column header as a string
        or multiple column headers as a list of strings.
    replacement : dict, optional
        A dictionary that is used to convert the headers to LingPy format.
        By default this parameter gets no value. In this case only, the function
        assigns it a default dictionary with some CLDF headers as keys and
        the corresponding LingPy headers as values.

    Returns
    -------
    str
        If a single CLDF header is passed, the corresponding LingPy header
        is returned. If the header is not found in 'replacement', it
        is converted to all caps.
    list
        If multiple CLDF headers are passed in a list, the corresponding LingPy
        headers are returned in a list. If a header is not found in 'replacement',
        that header is converted to all caps.

    Examples
    --------
    >>> cldf_to_lingpy('Form')
    'IPA'

    >>> cldf_to_lingpy('Notes')
    'NOTES'

    >>> cldf_to_lingpy('Notes', replacement={'Notes': 'LOG'})
    'LOG'

    >>> cldf_to_lingpy(['Form', 'Concept_ID', 'ID', 'Notes'])
    ['IPA', 'CONCEPT', 'REFERENCE', 'NOTES']
    """
    if replacement is None:
        replacement = {'Concept_ID': 'CONCEPT',
                       'Lect_ID': 'DOCULECT',
                       'Form': 'IPA',
                       'ID': 'REFERENCE',
                       'Segments': 'TOKENS'}
    if type(columns) == str:
        return replacement.get(columns, columns.upper())
    columns = [replacement.get(c, c.upper()) for c in columns]
    return columns


def lingpy_to_cldf(columns, replacement=None):
    """Turn LingPy column headers into CLDF column headers.

    Parameters
    ----------
    columns : str or list of str
        This is either a single LingPy column header as a string
        or multiple column headers as a list of strings.
    replacement : dict, optional
        A dictionary that is used to convert the headers to CLDF format.
        By default this parameter gets no value. In this case only, the function
        assigns it a default dictionary with some LingPy headers as keys and
        the corresponding CLDF headers as values.

    Returns
    -------
    str
        If a single LingPy header is passed, the corresponding CLDF header
        is returned. If the header is not found in 'replacement', it
        is converted to a title.
    list
        If multiple LingPy headers are passed in a list, the corresponding CLDF
        headers are returned in a list. If a header is not found in 'replacement',
        that header is converted to a title.

    Examples
    --------
    >>> lingpy_to_cldf('IPA')
    'Value'

    >>> lingpy_to_cldf('LOG')
    'Log'

    >>> lingpy_to_cldf('LOG', replacement={'LOG': 'Notes'})
    'Notes'

    >>> lingpy_to_cldf(['IPA', 'COGID', 'TOKENS', 'LOG'])
    ['Value', 'Cognate_Set', 'Segments', 'Log']
    """
    if replacement is None:
        replacement = {'REFERENCE': 'ID',
                       'CONCEPT': 'Concept_ID',
                       'DOCULECT': 'Lect_ID',
                       'COGID': 'Cognate_Set',
                       'IPA': 'Value',
                       'TOKENS': 'Segments'}
    if type(columns) == str:
        return replacement.get(columns, columns.title())
    columns = [replacement.get(c, c.title()) for c in columns]
    return columns


def no_separators_or_newlines(string, separator="\t"):
    r"""Replace new lines and separators with spaces, semicolons or tabs.

    Parameters
    ----------
    string : str
        A string containing new lines and separators such as tabs,
        and commas.
    separator : str, optional
        A string that defines the type of separator. By default this is
        set to tabs.

    Returns
    -------
    str
        The passed 'string' with replacements depending on the value of 'separator'.
        If 'separator' was set to tab:
            New lines replaced with spaces, tabs replaced with spaces.
        If 'separator' was set to comma:
            New lines replaced with tabs, commas replaced with semicolons.
        If 'separator' was set to anything else:
            New lines replaced with tabs, 'separator' replaced with tabs.

    Examples
    --------
    >>> no_separators_or_newlines('This\tis\nSparta!')
    'This is Sparta!'

    >>> no_separators_or_newlines('This,is\nSparta!', separator=',')
    'This;is    Sparta!'

    >>> no_separators_or_newlines('This;is\nSparta!', separator=';')
    'This   is  Sparta!'
    """
    if separator == "\t":
        string = string.replace("\n", " ")
        return string.replace("\t", " ")
    elif separator == ",":
        string = string.replace("\n", "\t")
        return string.replace(",", ";")
    else:
        string = string.replace("\n", "\t")
        return string.replace(separator, "\t")


def cldf(args):
    """Load a CLDF dataset and turn it into a LingPy word list file

    Sort by cognateset, for easier visual inspection of certain things I'm
    interested in.

    Parameters
    ----------
    args : Namespace
        A Namespace object with an 'args' property, which is a tuple of strings.
        The strings should be valid paths corresponding to resp. the metadata file of
        the CLDF data set and the LingPy word list (edictor file).

    Notes
    -----
        When this function is called, a new LingPy wordlist file is generated at
        the output path that is passed, based on the input metadata file of the CLDF data set.
    """
    input_file, output_file = args.args
    cogids = {None: 0}
    dataset = pycldf.dataset.Wordlist.from_metadata(input_file)

    try:
        cognate_set_iter = dataset["CognateTable"].iterdicts()
    except KeyError:
        cognate_set_iter = []
    cognate_set = {}
    for cognate_table_row in cognate_set_iter:
        cognate_table_row["COGNATESETTABLE_ID"] = cognate_table_row.pop("ID")
        form = cognate_table_row.pop("Form_ID")
        cognate_set[form] = cognate_table_row

    all_rows = []
    for i, row in enumerate(dataset["FormTable"].iterdicts()):
        try:
            cognate_table_row = cognate_set[row["ID"]]
            row.update(cognate_table_row)
        except KeyError:
            pass

        o_row = collections.OrderedDict()
        for key, value in row.items():
            if isinstance(value, str):
                # Strings need special characters removed
                o_row[cldf_to_lingpy(key)] = no_separators_or_newlines(value)
            else:
                try:
                    # Sequences (Alignment, Segments) need conversion and
                    # special characters removed
                    o_row[cldf_to_lingpy(key)] = no_separators_or_newlines(
                        " ".join(value))
                except TypeError:
                    # Other values are taken as-is
                    o_row[cldf_to_lingpy(key)] = value
        o_row["ID"] = i + 1
        if "COGID" not in o_row.keys():
            o_row["COGID"] = cogids.setdefault(row.get("Cognateset_ID"), len(cogids))
        all_rows.append(o_row)

        firstcols = ["ID", "COGID"]
        if i == 0:
            # Rearrange the headers so that 'ID' and 'COGID' are the first two columns.
            for header in reversed(firstcols):
                o_row.move_to_end(header, last=False)
            writer = csv.DictWriter(
                open(output_file, 'w', encoding='utf-8'), delimiter="\t",
                fieldnames=o_row.keys())
            writer.writeheader()
            
    try:
        all_rows = sorted(all_rows, key=lambda row: row["COGID"])
    except TypeError:
        # Incomparable COGIDs?
        pass
    for row in all_rows:
        writer.writerow(row)


def lingpy(args):
    """Load a Lingpy dataset and turn it into a CLDF word list file

    Parameters
    ----------
    args : Namespace
        A Namespace object with an 'args' property, which is a tuple of strings.
        The strings should be valid paths corresponding to resp. the metadata file of
        the Lingpy data set and the CLDF word list.

    Notes
    -----
        When this function is called, a new CLDF wordlist file is generated at
        the output path that is passed, based on the input Lingpy dataset.
    """
    # TODO: Finish this docstring.
    input_file, output_file = args.args
    reader = csv.DictReader(input_file, delimiter="\t")
    for i, row in enumerate(reader):
        if i == 0:
            # FIXME: Refactor 'writer' variable so it cannot be called if it is not defined yet.
            writer = csv.DictWriter(
                output_file, delimiter=",",
                fieldnames=[
                    lingpy_to_cldf(c)
                    for c in reader.fieldnames])
            writer.writeheader()
        writer.writerow({
            lingpy_to_cldf(key): value
            for key, value in row.items()})


if __name__ == "__main__":
    parser = ArgumentParser('lingpycldf', cldf, lingpy)
    sys.exit(parser.main())
