#!/usr/bin/env python

"""Automatically align similar forms"""

import copy

import numpy
import newick
import pandas
import pickle
import itertools

import sys
import argparse

from newick import Node

import infomapcog.dataio as dataio

def upgma(distance_matrix, names=None):
    """Cluster based on distance matrix dist using UPGMA

    That is, the Unweighted Pair Group Method with Arithmetic Mean algorithm

    If node names are given (not None), they must be a sequence of the same
    length as the size of the square distance_matrix.

    The edge lengths in the tree are not useful for the time being.
    """

    # Initialize nodes
    nodes = [Node(name) for name in (names or range(len(distance_matrix)))]

    # Iterate until the number of clusters is k
    nc = len(distance_matrix)
    while nc > 1:
        # Calculate the pairwise distance of each cluster, while searching for pair with least distance
        minimum_distance = numpy.inf
        i, j = 0, 1
        for i in range(nc-1):
            for j in range(i+1, nc):
                dis = distance_matrix[i, j]
                if dis < minimum_distance:
                    minimum_distance = dis
                    cluster = nodes[i], nodes[j]
                    indices = i, j
        # Merge these two nodes into one new node

        i, j = indices
        distance_matrix[i] = 0.5 * (distance_matrix[i]) + 0.5*(distance_matrix[j])
        distance_matrix[:,i] = 0.5 * (distance_matrix[:,i]) + 0.5*(distance_matrix[:,j])
        nodes[i] = Node.create(descendants=cluster)
        for c in cluster:
            c.length = distance_matrix[i,i]

        distance_matrix = numpy.delete(distance_matrix, j, 0)
        distance_matrix = numpy.delete(distance_matrix, j, 1)
        del nodes[j]

        nc -= 1
    return nodes[0]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", default=sys.stdin, nargs="?",
                        type=argparse.FileType('r'),
                        help="Input file containing word list")
    parser.add_argument("output", default=sys.stdout, nargs="?",
                        type=argparse.FileType('w'),
                        help="Output file to write segmented data to")
    parser.add_argument("--lodict", default=None,
                        type=argparse.FileType('rb'),
                        help="Phonetic segment similiarity dictionary")
    parser.add_argument(
        "--tokens", default="Tokens",
        help="Column name with tokenized (space-separated) values for coding")
    parser.add_argument("--asjp", action="store_const", const="ASJP",
                        dest="tokens",
                        help="Use ASJP classes for similarity coding")
    parser.add_argument("--cognate-col", default="Group",
                        help="Column containing the cognate classes")
    parser.add_argument("--guide-tree", type=argparse.FileType('r'),
                        help="Newick tree to use as guide tree for multi-alignment")
    parser.add_argument("--only-necessary", action='store_true', default=False,
                        help="Only align those classes that appear unaligned")
    args = parser.parse_args()

    if args.lodict is None:
        lodict = {}
    else:
        lodict = pickle.load(args.lodict)

    data = pandas.io.parsers.read_csv(
        args.input,
        sep="\t",
        na_values=[""],
        keep_default_na=False,
        encoding='utf-8',
        index_col=["English", "Language_ID", "Tokens"])

    if args.guide_tree:
        tree = newick.load(args.guide_tree)[0]
    else:
        # Calculate an UPGMA tree or something
        by_language = data.groupby("Language_ID")
        languages = []
        distance_matrix = numpy.zeros((len(by_language), len(by_language)))
        for (l1, (language1, data1)), (l2, (language2, data2)) in (
                itertools.combinations(enumerate(by_language), 2)):
            if language1 not in languages:
                languages.append(language1)
            print(language1, language2)
            c = 0
            shared_vocab = 0
            for concept in set(data1["Feature_ID"]) | set(data2["Feature_ID"]):
                c1 = set(data1["Cognate Set"][data1["Feature_ID"] == concept])
                c2 = set(data2["Cognate Set"][data2["Feature_ID"] == concept])
                shared_vocab += len(c1 & c2)/len(c1 | c2)
                c += 1

            distance_matrix[l1, l2] = 1-shared_vocab/c
            distance_matrix[l2, l1] = 1-shared_vocab/c
        languages.append(language2)
        tree = upgma(distance_matrix, languages)
        print(tree)
        open("tree.newick", "w").write(tree.newick)

    for i, cognateclass in data.groupby(args.cognate_col):
        if args.only_necessary and len(set([
                len(r.split()) for r in cognateclass["Alignment"]])) == 1:
            continue

        # Convert the data from a dataframe into a dict that
        # multi_align can work with. NOTE: By its current API,
        # infomapcog expects (L,C,V) tuples as keys.
        as_dict = [
            {(l, c, tuple(t.split()))
                for (c, l, t), row in cognateclass.iterrows()}]

        if len(cognateclass) == 1:
            language, concept, alg = as_dict[0].pop()
            data.set_value(
                (concept, language, ' '.join([a for a in alg if a])),
                "Alignment",
                " ".join([a for a in alg if a]))
            continue

        # Run the multi-alignment algorithm. Because it manipulates
        # the tree internally, putting the forms on its nodes, we pass
        # a copy of the tree so different groups don't come in conflict.
        for group, (languages, concepts, algs) in dataio.multi_align(
                as_dict, copy.deepcopy(tree),
                lodict=dataio.MaxPairDict(lodict),
                gop=-2.5, gep=-1.75).items():
            for language, concept, alg in zip(
                    languages, concepts, zip(*algs)):
                print(alg)
                data.set_value(
                    (concept, language, ' '.join([a for a in alg if a])),
                    "Alignment",
                    " ".join([a or '-' for a in alg]))

    data.to_csv(args.output,
                index=True,
                na_rep="",
                sep=",")
