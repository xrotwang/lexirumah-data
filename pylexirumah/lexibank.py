import json

import attr

from clldutils.path import Path
from clldutils.misc import lazyproperty

from pylexibank.dataset import Dataset as BaseDataset, Metadata as BaseMetadata

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

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):
        with self.cldf as ds:
            ds.add_sources()
            ds.add_concepts(id_factory=lambda c: c.number)
            for cid, concept, lid, gc, form, cogid in pb(self.raw.read_csv('output.csv')):
                ds.add_language(ID=lid.replace(' ', '_'), Name=lid, Glottocode=gc)
                for row in ds.add_lexemes(
                    Language_ID=lid.replace(' ', '_'),
                    Parameter_ID=cid,
                    Value=form,
                    Source=[SOURCE],
                    Cognacy=concept + '-' + cogid
                ):
                    ds.add_cognate(
                        lexeme=row,
                        Cognateset_ID=cogid,
                        Source=[SOURCE])
