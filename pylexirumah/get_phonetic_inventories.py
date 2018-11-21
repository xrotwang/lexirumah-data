import argparse
import collections
import pyclts

bipa = pyclts.TranscriptionSystem()

from pylexirumah import get_dataset, repository
parser = argparse.ArgumentParser(
    description="List the sound inventories contained in a CLDF Wordlist")
parser.add_argument("--dataset", default=None)
args = parser.parse_args()
dataset = get_dataset(args.dataset)

inventories = collections.defaultdict(collections.Counter)

c_language = dataset["FormTable", "languageReference"].name
c_segments = dataset["FormTable", "segments"].name

for row in dataset["FormTable"].iterdicts():
    normalized = [str(bipa[x]) for x in row[c_segments]]
    inventories[row[c_language]].update(normalized)

all = collections.Counter()
for language, inventory in inventories.items():
    print(language)
    for item, frequency in inventory.most_common():
        print("\t{:}\t{:d}".format(item, frequency))
    all.update(inventory)
    print()

print("Summa")
for item, frequency in all.most_common():
    print("\t{:}\t{:d}".format(item, frequency))
