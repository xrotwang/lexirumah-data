from lingpy import *
from lingpy.sequence.sound_classes import clean_string
from glob import glob
from clldutils.dsv import UnicodeReader
from clldutils.path import Path
import os
import re

def cldf2lingpy(path, delimiter="\t", quotechar='"'):
    
    with UnicodeReader(path, delimiter=delimiter, quotechar=quotechar) as reader:
        for line in reader:
            yield line

def load_dataset(dataset, extension=".tsv", delimiter="\t", quotechar='"',
        header=['CONCEPT_ID', 'CONCEPT', 'DOCULECT_ID', 'DOCULECT', 'FAMILY',
                'REGION', 'VALUE', 'COMMENT', 'ALIGNMENT', 'COGNATE_SET', 'SOURCE',
                'LOAN', 'REFERENCE', 'ORIGINAL_FILE']):

    idx = 1
    D = {}
    for dirpath, dnames, fnames in os.walk(dataset):
        for f in fnames:
            if os.path.splitext(f)[1] == extension:
                f = os.path.join(dirpath, f)
                print(f)
                with UnicodeReader(
                     f,
                     delimiter=delimiter,
                     quotechar=quotechar) as rd:
                    for i, line in enumerate(rd):
                        if i == 0:
                            if len(line) <= len(header)-1:
                                pad = [""] * (len(header)-len(line)-1)
                            elif len(line) > len(header):
                                raise ValueError(f)
                        else:
                            D[idx] = [re.sub(r"\s+", " ", x) for x in line] + pad + [f]
                            if len(D[idx])!=len(header):
                                raise ValueError(f)
                            idx += 1
                print(idx)
    D[0] = header 
    
    return Wordlist(D)


