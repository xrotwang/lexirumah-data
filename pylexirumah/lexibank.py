import json

import attr

from pathlib import Path
from clldutils.misc import lazyproperty

from pylexibank import Dataset as BaseDataset
from pylexibank import LexibankMetadata as BaseMetadata

class Metadata(BaseMetadata):
    @classmethod
    def from_cldf_metadata(cl, meta):
        data = cl(title=meta["dc:title"],
                  description=meta["dc:description"],
                  # citation=...,
                  license=meta["dc:license"],
                  url="http://{:}".format(meta["special:domain"]),
                  # aboutUrl=...,
                  conceptlist=meta["special:conceptlist"],
                  # lingpy_schema=...,
                  # derived_from=...,
                  # related=...,
                  source=meta["dc:source"],
                  )
        return data


class Dataset(BaseDataset):
    dir = Path(__file__).parent.parent
    id = "lexirumah"

    @lazyproperty
    def metadata(self):
        return Metadata.from_cldf_metadata(json.load((self.dir / 'cldf/cldf-metadata.json').open()))

    def cmd_download(self, args):
        # If you got here, this dataset is downloaded.
        pass

    def cmd_makecldf(self, args):
        # If you got here, this dataset is already in CLDF.
        pass
