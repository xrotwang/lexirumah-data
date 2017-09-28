from operator import attrgetter
from collections import defaultdict, OrderedDict, Counter

from clldutils.path import Path

REPOS_PATH = Path(__file__).parent.parent
from clldutils import dsv


def to_dict(iterobjects, key=attrgetter('id')):
    """
    Turns an iterable into an `OrderedDict` mapping unique keys to items.

    :param iterobjects: an iterable to be turned into the values of the dictionary.
    :param key: a callable which creates a key from an item.
    :returns: `OrderedDict`
    """
    res, keys = OrderedDict(), Counter()
    for obj in iterobjects:
        k = key(obj)
        res[k] = obj
        keys.update([k])
    if keys:
        k, n = keys.most_common(1)[0]
        if n > 1:
            raise ValueError('non-unique key: %s' % k)
    return res


def read_all(fname, **kw):
    kw.setdefault('delimiter', '\t')
    if not kw.get('dicts'):
        kw.setdefault('namedtuples', True)
    return list(dsv.reader(fname, **kw))


def read_dicts(fname, schema=None, **kw):
    kw['dicts'] = True
    res = read_all(fname, **kw)
    if schema:
        def identity(x):
            return x
        colspec = {}
        for col in schema['columns']:
            conv = {
                'integer': int,
                'float': float,
            }.get(col['datatype'])
            colspec[col['name']] = conv or identity
        res = [{k: colspec[k](v) for k, v in d.items()} for d in res]
    return res

