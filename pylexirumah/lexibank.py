from clldutils.path import Path
from pylexibank.dataset import Dataset as BaseDataset


class Dataset(BaseDataset):
    dir = Path(__file__).parent.parent
    id = "lexirumah"

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):
        pass

