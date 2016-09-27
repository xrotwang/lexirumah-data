from lingpy import Wordlist, LexStat, Alignments, ipa2tokens

wl = Wordlist('data-example.tsv')
wl.add_entries('tokens', 'value', lambda x: ipa2tokens(''.join(x)) if x not in ['', '-'] else '' )
wl.output('tsv', subset=True, rows=dict(value="not in ['', '-']"), filename='data-example-2')
lex = LexStat('data-example-2.tsv', check=True)
lex.cluster(method='sca', threshold=0.45)
alms = Alignments(lex, ref='scaid')
alms.align()
alms.output('tsv', ignore='all', prettify=False)
