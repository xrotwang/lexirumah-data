"""pylexirumah: API scripts for LexiRumah"""

from pycldf import Dataset
from clldutils.path import Path

# It would be good to keep this more configurable, and in one place in pylexirumah.
repository = (Path(__file__).parent.parent /
              "cldf" / "cldf-metadata.json")

def get_dataset(fname=None):
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    pycldf.Dataset
    """
    if fname is None:
        fname = repository
    else:
        fname = Path(fname)
    if not fname.exists():
        raise FileNotFoundError(
            '{:} does not exist'.format(fname))
    if fname.suffix == '.json':
        return Dataset.from_metadata(fname)
    return Dataset.from_data(fname)


