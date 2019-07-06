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
from segments import Tokenizer, Profile

bipa = pyclts.TranscriptionSystem("bipa")
sounds = list(bipa.sounds)
sounds.extend([])
tokenizer = Tokenizer(Profile(*({"Grapheme": x, "mapping": x} for x in sounds)))

from pylexirumah import get_dataset, repository


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
            yield form.strip().strip("_")
        for form in resolve_brackets(string[:opening] + string[opening+1:closing] + string[closing+1:]):
            yield form.strip().strip("_")
    else:
        yield string


class Transducer:
    def __init__(self, rules):
        self.rules = rules
        self.wordboundary = "_"

    def __repr__(self):
        return "Transducer({:})".format(self.rules)

    def __str__(self):
        return " / ".join("{:} → {:}".format(before, after) for before, after in self.rules)

    def __call__(self, line):
        """Apply tranducer rules, left to right then first to last, to line.

        Apply the first fitting replacement rule (a before/after pair) to the
        leftmost bit of the string, then shift right past the replaced section and
        again apply the first matching rule, and so forth until you reach the end
        of the string. Note this is different to applying each rule in order
        whereever it fits, see the examples!

        Examples
        --------

        >>> string = "qaqqqqq"
        >>> rules = [("qq", "a"), ("aq", "b")]
        >>> Transducer(rules)(string)
        'qbaa'
        >>> for before, after in rules:
        ...   string.replace(before, after)
        'qaab'

        """
        line = self.wordboundary + line + self.wordboundary
        start = 0
        output = ""
        while start < len(line):
            oldStart = start
            for (left, right) in self.rules:
                match = False
                end = len(line) + 1
                while end > start:
                    if left == line[start:end]:
                        output += right
                        start = end
                        match = True
                        break
                    else:
                        end -= 1
                if match:
                    break
            if start == oldStart:
                output += line[start]
                start += 1
        return output.strip(self.wordboundary)

    def undo(self, line):
        """Undo – as much as possible, due to mergers – the effect this.

        Assume that every instance of a rule result on the right hand side is
        the result of application of this transducer. Assume furthermore that
        every pattern matched has been produced by the first rule that could
        produce such a pattern.

        >>> string = "qaqqqqq"
        >>> rules = [("qq", "a"), ("aq", "b")]
        >>> t = Transducer(rules)
        >>> t(string)
        'qbaa'
        >>> t.undo(t(string)) == string
        True

        """
        line = self.wordboundary + line + self.wordboundary
        start = 0
        output = ""
        while start < len(line):
            oldStart = start
            for (right, left) in self.rules:
                match = False
                end = len(line) + 1
                while end > start:
                    if left == line[start:end]:
                        output += right
                        start = end
                        match = True
                        break
                    else:
                        end -= 1
                if match:
                    break
            if start == oldStart:
                output += line[start]
                start += 1
        return output.strip(self.wordboundary)


def load_orthographic_profile(transducer_files, root=repository.parent, transducer_cache={}):
    if transducer_files is None:
        return None

    orthographic_profile = []
    for file in transducer_files:
        if not file:
            continue
        try:
            transducer_cache[file]
        except KeyError:
            # That file is not in our cache yet, we have to load it and
            # turn it into a function.
            substitutions = []
            for rule in (root / file).open(encoding="utf-8"):
                rule = rule.strip("\n")
                rule = rule.strip("\r")
                if "//" in rule:
                    rule = rule[:rule.index("//")]
                if not rule.strip():
                    continue
                if "[" in rule or "#def" in rule:
                    raise NotImplementedError("Context groups are not supported yet.")
                try:
                    before, after = rule.split("\t")
                except ValueError:
                    print(rule)
                    raise
                substitutions.append((before, after))
            transducer_cache[file] = Transducer(substitutions)
        orthographic_profile.append(transducer_cache[file])
    return orthographic_profile


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import word lists from a new source into LexiRumah.")
    parser.add_argument("directory", nargs="?",
                        type=Path, default="./",
                        help="The folder containing the wordlist description,"
                        " derived from the standard template. (default: The"
                        " current working directory.)")
    parser.add_argument("--wordlist",
                        type=Path, default=repository,
                        help="The Wordlist to expand. (default: LexiRumah.)")
    parser.add_argument("--override",
                        default='none',
                        choices=["none", "all", "ask", "ask-per-source", "mark"],
                        help="Instead of just checking all forms and reporting"
                        "those that don't match, just overwrite everything"
                        "systematically.")
    parser.add_argument("--check-stress",
                        default=False, action="store_true",
                        help="By default, we ignore stress marks in comparisons."
                        " This option dumbs down the comparisons to report changes"
                        " in stress marking.")
    parser.add_argument("--match",
                        default=None,
                        help="Check only forms in which one of the columns"
                        " given has this substring.")

    parser.add_argument(
        "--step",
        default=["report", "override", "fill"],
        type=str.split,
        help="""What to do for the 3 checking steps Value→Form, Form→Segments and
        Form→Orthography: Keep <quiet>, <report> differences, <override>
        differences or <fill> empty cells. A list of three space-separated
        entries from these options. (Default: report override fill)""")
    args = parser.parse_args()

    if args.check_stress:
        def drop_stress(string):
            return string
    else:
        def drop_stress(string):
            return string and string.replace("ˈ", "").replace("ˌ", "")
    if args.override == 'none':
        def maybe_extend(collection, new, old):
            collection.extend(old)
    elif args.override == 'all':
        def maybe_extend(collection, new, old):
            collection.extend(new)
    elif args.override == 'ask-per-source':
        def maybe_extend(collection, new, old):
            if not new:
                return
            if input() == "y":
                collection.extend(new)
            else:
                collection.extend(old)
    elif args.override == 'ask':
        def maybe_extend(collection, new, old):
            for new_row, old_row in zip(new, old):
                if new_row == old_row:
                    collection.append(old_row)
                else:
                    print(old_row)
                    print(new_row)
                    if input() == "y":
                        collection.append(new_row)
                    else:
                        collection.append(old_row)
    elif args.override == 'mark':
        def maybe_extend(collection, new, old):
            for new_row, old_row in zip(new, old):
                try:
                    if new_row != old_row:
                        old_row[c_source].insert(0, "corr")
                except AttributeError:
                    old_row[c_source].insert(0, "corr")
                collection.append(old_row)

    dataset = get_dataset(args.wordlist)
    if dataset.module != 'Wordlist':
        raise ValueError(
            "This script can only import wordlist data to a CLDF Wordlist.")

    language_orthographies = {None: None}

    c_languageid = dataset["LanguageTable", "id"].name

    for line in dataset["LanguageTable"].iterdicts():
        transducer_files = line.get("Orthography") # This property is not codified by CLDF
        if not transducer_files:
            language_orthographies[line[c_languageid]] = None
        else:
            language_orthographies[line[c_languageid]] = load_orthographic_profile(transducer_files)

    transcription_systems = {None: None}

    c_segments = dataset["FormTable", "segments"].name
    c_source = dataset["FormTable", "source"].name
    c_language = dataset["FormTable", "languageReference"].name
    c_value = dataset["FormTable", "value"].name
    c_form = dataset["FormTable", "form"].name
    c_value = dataset["FormTable", "value"].name
    c_id = dataset["FormTable", "id"].name
    c_orth = "Local_Orthography" # This property is not codified by CLDF

    message = print

    lines = []
    original_lines_of_this_source = []
    new_lines_of_this_source = []
    previous_source = None
    for line in dataset["FormTable"].iterdicts():
        # Load the line's main source, that is, the first entry in the sources list.

        if args.match:
            for value in line.values():
                if args.match in str(value):
                    break
            else:
                new_lines_of_this_source.append(line)
                continue

        try:
            main_source = line[c_source][0]
        except (IndexError, KeyError):
            main_source = None
            message("Source not found for form {:}".format(line[c_id]))

        if main_source != previous_source:
            maybe_extend(
                lines,
                new_lines_of_this_source,
                original_lines_of_this_source)
            original_lines_of_this_source = []
            new_lines_of_this_source = []
            previous_source = main_source
            print(main_source)

        original_lines_of_this_source.append(line.copy())

        if not line[c_value] or line[c_value] == '-':
            if args.step[1] == "quiet":
                pass
            else:
                if line[c_form]:
                    message("Form {:} is not given in source, but had a form "
                            "{:} specified.".format(line[c_id], line[c_form]))
                line[c_form] = None

        # Load the orthographic profile of that main source.
        try:
            # First, see whether we have it in cache
            orthographic_profile = transcription_systems[main_source]
        except KeyError:
            # Otherwise, look up the name of the orthographic profile specified in
            # the source metadata.
            source = dataset.sources[main_source]
            try:
                transducer_files = source["orthographic_profile"].split(":")
            except KeyError:
                # It is permitted to not specify an orthographic profile in a
                # source. Then we assume the source is in ideosyncratic and rely on
                # forms being given explicitly. NOTE how this is different from
                # specifying an empty orthographic profile: An empty profile means
                # that no transducers are applied, i.e. that the data is already in
                # IPA.
                transducer_files = None

            # Now we get the list of transducer functions to apply.
            orthographic_profile = load_orthographic_profile(transducer_files)
            if orthographic_profile:
                print(*(str(o) for o in orthographic_profile))
            transcription_systems[main_source] = orthographic_profile

        if args.step[0] == 'quiet':
            form = line[c_form] or ''
        else:
            if orthographic_profile is None:
                # There is no way to do automatic transcription: Check that a form is given.
                form = line[c_form] or ''
                if not form:
                    message(
                        "Form {:} has ideosyncratic orthography and original value"
                        " <{:}>, but no form was given.".format(line[c_id], line[c_value]))
            else:
                if "/" in line[c_value]:
                    message(
                        "Form {:} is listed as <{:}>, which is likely an "
                        "invalid cell containing two different forms.".format(line[c_id], line[c_value]))

                # Apply substitutions to form
                form = (line[c_value] or '').strip()
                for transducer in orthographic_profile:
                    form = transducer(form)

            if form != line[c_form]:
                resolutions = [drop_stress(r) for r in resolve_brackets(form)]
                if len(resolutions) > 1 and drop_stress(line[c_form]) in resolutions:
                    variant = resolutions.index(drop_stress(line[c_form]))
                    resolution = list(resolve_brackets(form))[variant]
                    if len(resolution) > len(line[c_form]):
                        message("Form {:} has original value <{:}>, which contains brackets. Canonically, it would be [{:}] according to the orthography. Variant form [{:}] was given explicitly. Taking form [{:}] as compromise.".format(line[c_id], line[c_value], form, line[c_form], resolution))
                        form = resolution
                    else:
                        message("Form {:} has original value <{:}>, which contains brackets. Canonically, it would be [{:}] according to the orthography. Variant form [{:}] was given explicitly.".format(line[c_id], line[c_value], form, line[c_form]))
                        form = line[c_form]
                elif not line[c_form]:
                    if len(resolutions) > 1:
                        form = [drop_stress(r) for r in resolve_brackets(form)][0]
                    message(
                        "Form {:} has original value <{:}>, which corresponds to"
                        " [{:}] according to the orthography; no form given."
                        "".format(line[c_id], line[c_value], form, line[c_form]))
                elif line[c_form] != drop_stress(form):
                    message(
                        "Form {:} has original value <{:}>, which should correspond to"
                        " [{:}] according to the orthography, but form [{:}] was given."
                        "".format(line[c_id], line[c_value], form, line[c_form]))

            if args.step[0] == "override" or (args.step[0] == "fill" and not line[c_form]):
                line[c_form] = form

        # Segment form and check with BIPA The segments cannot deal cleanly with
        # suprasegmentals (syllable boundaries, syllable stress), so those are
        # ignored explicitly or implicitly.
        if args.step[1] == "quiet":
            segments = [bipa[x] for x in line[c_segments]]
        else:
            try:
                segments = [bipa[x]
                            for part in (line[c_form] or '').split(".")
                            for x in tokenizer(part, ipa=True).split()]
            except IndexError:
                message(
                    "Form {:} [{:}] contains non-BIPA segment '{:}'.".format(
                        line[c_id], form, s.source))
                segments = [bipa[x] for x in line[c_form]]

            for s in segments:
                if isinstance(s, pyclts.models.UnknownSound):
                    message(
                        "Form {:} [{:}] contains non-BIPA segment '{:}'.".format(
                            line[c_id], form, s.source))

            if (line[c_segments]) and ([str(bipa[x]) for x in line[c_segments]] !=
                [str(x) for x in segments]):
                    message(
                        "Form {:} has form [{:}], which should correspond to segments"
                        " [{:}], but segments [{:}] were given."
                        "".format(
                            line[c_id],
                            line[c_form],
                            " ".join(map(str, segments)),
                            " ".join([s or '' for s in line[c_segments]])))

            if args.step[1] == "override" or (args.step[1] == "fill" and not line[c_segments]):
                line[c_segments] = segments

        if args.step[2] == "quiet":
            pass
        else:
            language_orthography = language_orthographies[line[c_language]] or ""

            # Check the form's orthography.
            if not language_orthography:
                if not line[c_orth]:
                    message("Form {:} [{:}] is not given in the local orthography,"
                            " and no way to derive it was given.".format(
                                line[c_id], line[c_form]))

            # For checking, transform the local orthography to the form by
            # applying the language's orthography.
            orth_form = line[c_orth] or ""
            match = False
            if orth_form:
                expected_form = orth_form
                for transducer in language_orthography:
                    expected_form = transducer(expected_form)

                if drop_stress(expected_form) == drop_stress(line[c_form]):
                    match = True

            # If that does not work, try tranforming the form to the local
            # orthography by reverse-applying the language's orthography.
            expected_orth = line[c_form]
            for transducer in reversed(language_orthography):
                expected_orth = transducer.undo(expected_orth)
            expected_orth = expected_orth.replace("_", " ").replace("+", "-").strip()

            if match:
                pass
            elif expected_orth != orth_form and orth_form:
                message(
                    "Form {:} is given in the local orthography as <{:}>, but"
                    " phonetics [{:}] would correspond to <{:}>.".format(
                        line[c_id], line[c_orth], form, expected_orth))
            elif orth_form:
                pass
            else:
                message(
                    "Form {:} is not given in the local orthography. From its"
                    " phonetics [{:}], taking <{:}>.".format(
                        line[c_id], form, expected_orth))

            if args.step[2] == "override" or (args.step[2] == "fill" and not line[c_orth]):
                line[c_orth] = expected_orth

        new_lines_of_this_source.append(line)

    maybe_extend(
        lines,
        new_lines_of_this_source,
        original_lines_of_this_source)

    if args.override != 'none':
        dataset["FormTable"].write(lines)
