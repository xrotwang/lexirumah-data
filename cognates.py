from lingpy import Wordlist, LexStat, Alignments, ipa2tokens
from lingpy.sequence.sound_classes import clean_string
from util import load_dataset
from collections import defaultdict

# load wordlist using the function in utils
wl = load_dataset('datasets')

# check basic params
print('[i] Wordlist has {0} languages and {1} concepts in {2} entries.'.format(
    wl.width,
    wl.height,
    len(wl)))

# clean strings to count the segments
segments = defaultdict(int)
# error log
log = []
deletes = [] # list of keys that we won't need, as they are empty

# general replacement using s.replace(x, y)
PREPARSE = [
        ("'", 'ˈ'),
        ('Ɂ', 'ʔ'),
        (':', 'ː'),
        ('ɜ', 'ɜ'),
        ]
# iterate and count stuff, if words have multiple entries, split them and add
# them
addtokens = {}
for k in wl:
    tokens = []
    stop = False
    word = wl[k, 'value']
    # delete condition, potentially expand
    if word in ['', '(no data)', '-']:
        stop = True
        deletes += [k]
    # check for leading comma, an annoying error
    if any([word.startswith(x) for x in ',;']):
        word = word[1:]
    # check for ending comma
    if any([word.endswith(x) for x in ',;']):
        word = word[:-1]
    # check for bracket start end
    if not stop and word[0]+word[-1] == '()':
        stop = True
        deletes += [k]
    if not stop:
        try:
            tokens = clean_string(word, preparse=PREPARSE)
        except IndexError:
            log += ['[{0:4}] not parseable: «{1}»'.format(
                k, word)]
            stop = True
    if not stop:
        if len(tokens) > 1:
            log += ['[{0:4}] has {1} words: «{2}»'.format(
                k, len(tokens), word)]
        if not tokens[0].strip():
            log += ['[{0:4}] is empty: «{1}»'.format(k, word)]

        for segment in tokens[0]:
            segments[segment] += 1

    if tokens:
        addtokens[k] = tokens[0]
    else:
        addtokens[k] = '?'

wl.add_entries('segments', addtokens, lambda x: x)
# save wordlist, ignore lines which are empty
wl.output('tsv', filename='tap-cleaned', subset=True, rows=dict(
    ID = 'not in '+str(deletes)))

with open('errors.log', 'w') as f:
    f.write('\n'.join(log))

with open('segments.log', 'w') as f:
    for a, b in sorted(segments.items(), key=lambda x: x[1]):
        f.write('{0}\t{1}\n'.format(a, b))

# compute cognates
lex = LexStat('tap-cleaned', segments='segments')
print('[i] loaded lexstat')
lex.cluster(method='sca', threshold=0.45, ref='cogid')

# align data
alm = Alignments(lex, ref='cogid')
alm.align(override=True)
alm.output('tsv', filename='tap-aligned', ignore='all', prettify=False)


