from lingpy import *
from lingpy.sequence.sound_classes import clean_string
from glob import glob
from clldutils.dsv import UnicodeReader
from clldutils.path import Path

def cldf2lingpy(path, delimiter="\t", quotechar='"'):
    
    with UnicodeReader(path, delimiter=delimiter, quotechar=quotechar) as reader:
        for line in reader:
            yield line

def load_dataset(dataset, extension="tsv", delimiter="\t", quotechar='"',
        header=['CONCEPT_ID', 'CONCEPT', 'DOCULECT_ID', 'DOCULECT', 'FAMILY',
            'REGION', 'VALUE', 'ALIGNMENT', 'COGNATE_SET', 'SOURCE']):

    files = glob(Path(dataset, '*').as_posix()+extension)
    idx = 1
    D = {}
    for f in files:
        with UnicodeReader(f, delimiter=delimiter, quotechar=quotechar) as rd:
            for i, line in enumerate(rd):
                if i == 0:
                    header = line
                else:
                    D[idx] = line
                    idx += 1
    D[0] = header 
    
    return Wordlist(D)


