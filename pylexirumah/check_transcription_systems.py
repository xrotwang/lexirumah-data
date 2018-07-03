#!/usr/bin/env python

import sys
import argparse
import itertools
from collections import OrderedDict
from clldutils.path import Path
import numpy as np

import csvw
import xlrd
import pycldf

import pyclts

bipa = pyclts.TranscriptionSystem()

from pylexirumah import (get_dataset, repository)

parser = argparse.ArgumentParser(description="Import word lists from a new source into LexiRumah.")
parser.add_argument("directory", nargs="?",
                    type=Path, default="./",
                    help="The folder containing the wordlist description,"
                    " derived from the standard template. (default: The"
                    " current working directory.)")
parser.add_argument("--wordlist",
                    type=Path, default=repository,
                    help="The Wordlist to expand. (default: LexiRumah.)")
args = parser.parse_args([])

dataset = get_dataset(args.wordlist)
if dataset.module != 'Wordlist':
    raise ValueError(
        "This script can only import wordlist data to a CLDF Wordlist.")


def needleman_wunsch(x, y, lodict={}, gop=-2.5, gep=-1.75, local=False, indel=''):
    """Needleman-Wunsch algorithm with affine gaps penalties.

    This code implements the NW algorithm for pairwise string
    alignment with affine gap penalties.

    'lodict' must be a dictionary with all symbol pairs as keys and
    match scores as values, or a False value (including an empty
    dictionary) to denote (-1, 1) scores. gop and gep are gap
    penalties for opening/extending a gap; alternatively, you can set
    'gop' to None and provide element/gap alignment costs.
    indel takes the character used to denote an indel.

    Returns the alignment score and one optimal alignment.

    >>> needleman_wunsch("AAAAABBBB", "AACAABBCB")
    (5.0, [('A', 'A'), ('A', 'A'), ('A', 'C'), ('A', 'A'), ('A', 'A'), ('B', 'B'), ('B', 'B'), ('B', 'C'), ('B', 'B')])
    >>> needleman_wunsch("banana", "mancala", local=True)
    (2.0, [('a', 'a'), ('n', 'n')])
    >>> needleman_wunsch("abc", "t", lodict={('a', ''): 0, ('b', ''): -2, ('c', ''): -0.5}, gop=None)
    (-1.5, [('a', ''), ('b', 't'), ('c', '')])

    """
    n, m = len(x), len(y)
    dp = np.zeros((n + 1, m + 1))
    pointers = np.zeros((n + 1, m + 1), np.int32)
    if not local:
        for i1, c1 in enumerate(x):
            if gop is None:
                dp[i1 + 1, 0] = lodict.get((c1, indel), gep)
            else:
                dp[i1 + 1, 0] = dp[i1, 0]+(gep if i1 + 1 > 1 else gop)
            pointers[i1 + 1, 0] = 1
        for i2, c2 in enumerate(y):
            if gop is None:
                dp[0, i2 + 1] = lodict.get((indel, c2), gep)
            else:
                dp[0, i2 + 1] = dp[0, i2]+(gep if i2 + 1 > 1 else gop)
            pointers[0, i2 + 1] = 2
    for i1, c1 in enumerate(x):
        for i2, c2 in enumerate(y):
            match = dp[i1, i2] + lodict.get(
                (c1, c2),
                1 if c1 == c2 else -1)
            insert = dp[i1, i2 + 1] + (
                lodict.get((c1, indel), gep) if gop is None else
                gep if pointers[i1, i2 + 1] == 1 else gop)
            delet = dp[i1 + 1, i2] + (
                lodict.get((indel, c2), gep) if gop is None else
                gep if pointers[i1 + 1, i2] == 2 else gop)
            pointers[i1 + 1, i2 + 1] = p = np.argmax([match, insert, delet])
            max_score = [match, insert, delet][p]
            if local and max_score < 0:
                max_score = 0
            dp[i1 + 1, i2 + 1] = max_score
    alg = []
    if local:
        i, j = np.unravel_index(dp.argmax(), dp.shape)
    else:
        i, j = n, m
    score = dp[i, j]
    while (i > 0 or j > 0):
        pt = pointers[i, j]
        if pt == 0:
            i -= 1
            j -= 1
            alg = [(x[i], y[j])] + alg
        if pt == 1:
            i -= 1
            alg = [(x[i], indel)] + alg
        if pt == 2:
            j -= 1
            alg = [(indel, y[j])] + alg
        if local and dp[i, j] == 0:
            break
    return score, alg


def ideosyncratic(string):
    raise NotImplementedError


def replace(replacements):
    def apply(string):
        for before, after in replacements:
            string = string.replace(before, after)
        return string
    return apply


def remove_bracketed_material(string):
    while "(" in string:
        opening = string.index("(")
        closing = string.index(")")
        assert opening < closing
        string = string[:opening] + string[closing+1:]
    return string.strip().strip("_")


def change_accent_stress_marks(string):
    string = replace([
        ("á", "ˈa"),
        ("é", "ˈe"),
        ("í", "ˈi"),
        ("ó", "ˈo"),
        ("ú", "ˈu")
    ])(string)
    try:
        stress = string.index("́")
        string = string[:stress-1] + "ˈ" + string[stress-1] + string[stress:]
    except ValueError:
        pass
    return string

profile_functions = {
    "accent-marks-stress": change_accent_stress_marks,
    "include-bracketed": replace([("(", ""), (")", "")]),
    "american-j": replace([("j", "ʤ"), ("y", "j")])
}

transcription_systems = {}

c_source = dataset["FormTable", "source"].name

lines = []
possible_duplicates = []
previous_clean_form = None
previous_line = {"Concept_ID": None}
for line in dataset["FormTable"].iterdicts():
    try:
        main_source = line[c_source][0]
    except IndexError:
        print(line["ID"])
        lines.append(line)
        continue
    try:
        orthographic_profile = transcription_systems[main_source]
    except KeyError:
        source = dataset.sources[main_source]
        try:
            profile = source["orthographic_profile"]
        except KeyError:
            profile = None
        if profile:
            orthographic_profile = profile_functions[profile]
        else:
            orthographic_profile = None
        print(main_source, orthographic_profile)
        transcription_systems[main_source] = orthographic_profile
    form = line["Form"]
    if orthographic_profile is not None:
        # Load orthographic profile
        # Apply substitutions to form
        try:
            form = orthographic_profile(form)
        except NotImplementedError:
            print(line["ID"])
            lines.append(line)
            continue
        except ValueError as e:
            print(e)
            print(line["ID"])
            line["Comment"] = (line["Comment"] + "; Invalid IPA") if line["Comment"] else "Invalid IPA"
            lines.append(line)
            continue
    form = form.strip()
    # Normalize length markers
    form = form.replace(":", "ː")
    # Normalize word boundary markers
    form = form.replace(" ", "_")
    form = form.replace("-", "_")
    # Remove bracketed material
    form = remove_bracketed_material(form)
    segments = []
    for letter in form:
        # if letter == "ː":
        #    letter = previous_letter
        if letter in ["ˈ", "'", ",", "ˌ"]:
            continue
        if letter in ["."]:
            # Syllabic boundary marker
            continue
        sound = bipa[letter]
        if isinstance(sound, pyclts.models.UnknownSound):
            try:
                segments[-1] = bipa[segments[-1].grapheme + letter]
            except (IndexError, AttributeError):
                line["Comment"] = (line["Comment"] + "; Invalid IPA") if line["Comment"] else "Invalid IPA"
                lines.append(line)
        else:
            segments.append(sound)
            previous_letter = letter
    line["Segments"] = [s for s in line["Segments"] if s]
    old_clean_form = "".join(line["Segments"]).replace(" ", "_").strip("_")
    new_clean_form = "".join(str(s) for s in segments).replace(" ", "_").strip("_")
    if old_clean_form != new_clean_form:
        diff, align = needleman_wunsch(line["Segments"], [str(s) for s in segments])
        print(line["ID"])
        print(old_clean_form, new_clean_form, line["Form"])
        print(*["{:3s}".format(x) for x, y in align])
        print(*["{:3s}".format(y) for x, y in align])
        print(diff)
    line["Segments"] = [str(s) for s in segments]
    if all([previous_clean_form == new_clean_form,
            previous_line["Concept_ID"] == line["Concept_ID"],
            "(" in line["Form"]]):
        possible_duplicates.append(line)
    else:
        lines.append(line)
    previous_clean_form = new_clean_form
    previous_line = line

dataset["FormTable"].write(lines)
