from pylexirumah.util import get_dataset, repository

lexirumah = get_dataset(repository)

j = []
y = []
phonology = set()
for row in lexirumah["FormTable"].iterdicts():
    if row["Source"] == ['keraf1978']:
        form = row["Form"]
        if "j" in form:
            j.append(row)
        if "y" in form:
            y.append(row)

        phonology |= form
