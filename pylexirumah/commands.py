from clldutils.clilib import command

from .api import LexiRumah

@command()
def validate(args):
    api = LexiRumah(args.data)
    for wl in api.wordlists.values():
        item = list(wl.metadata)
        if set(items[0].keys()) != set(c.name for c in wl.metadata.tableSchema.columns):
            print('unspecified column in word list {0}'.format(wl.id))
