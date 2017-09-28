"""pylexirumah: API for accessing LexiRumah data."""

from clldutils.path import Path
from clldutils.apilib import API
from clldutils.misc import cached_property

from .util import REPOS_PATH, to_dict, read_dicts

class LexiRumah(API):
    """API class for accessing LexiRumah.

    This provides a python-object-level interface to languages, bibliography
    data, metadata and word forms in LexiRumah."""
    def __init__(self, repos=None):
        """API object.

        :param repos: Path to the LexiRumah data dump"""
        API.__init__(self, repos or REPOS_PATH)

    def data_path(self, *comps):
        """Return a file system path for a repository path.
        """
        return self.path('lexirumah-data', *comps)

    @cached_property()
    def wordlists(self):
        """The dict mapping Wordlist IDs to Wordlist instances"""
        return to_dict(
            Wordlist(api=self, **lowercase(d))
            for d in read_dicts(self.data_path('wordlists.tsv')))
