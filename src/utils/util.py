import random

import networkx as nx
import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold
from torch.jit.annotations import TensorType


class S2VGraph(object):
    def __init__(self, g: nx.Graph, label: int, node_tags: List[int] = None, node_features: TensorType = None):
        '''
            g: a networkx graph
            label: an integer graph label
            node_tags: a list of integer node tags
            node_features: a torch float tensor, one-hot representation of the tag that is used as input to neural nets
            edge_mat: a torch long tensor, contain edge list, will be used to create torch sparse tensor
            neighbors: list of neighbors (without self-loop)
        '''
        self.label = label
        self.g = g
        self.node_tags = node_tags
        self.neighbors: List[List[int]] = []
        self.node_features = node_features
        self.edge_mat: TensorType = 0

        self.max_neighbor: int = 0


def load_data(dataset: str, degree_as_tag: bool = False):
    '''
        dataset: name of dataset
        test_proportion: ratio of test train split
        seed: random seed for random splitting of dataset
    '''

    print('loading data')
    graph_list: List[S2VGraph] = []
    label_dict: Dict[int, int] = {}
    # {real_label : index}
    node_labels: Dict[int, int] = {}

    with open(dataset, 'r') as f:
        n_graphs = int(f.readline().strip())
        for _ in range(n_graphs):
            graph_row = f.readline().strip().split()
            n_nodes, graph_label = [int(w) for w in graph_row]
            # register graph label
            if not graph_label in label_dict:
                mapped = len(label_dict)
                label_dict[graph_label] = mapped
            g = nx.Graph()
            node_tags = []
            node_features = []
            n_edges = 0
            # for each node in the graph
            for j in range(n_nodes):
                # add the index (starts at 0 to n_nodes-1)
                g.add_node(j)
                node_row = f.readline().strip().split()

                # check for node features, most dont have
                tmp = int(node_row[1]) + 2
                if tmp == len(node_row):
                    # normal case (node label, n_edges, [edges])
                    # no node attributes
                    node_row = [int(w) for w in node_row]
                    attr = None
                else:
                    # ? no idea what this is
                    node_row,  = [int(w) for w in node_row[:tmp]]
                    attr = np.array([float(w) for w in node_row[tmp:]])

                # node label
                if not node_row[0] in node_labels:
                    mapped = len(node_labels)
                    node_labels[node_row[0]] = mapped
                # append the node label class index
                node_tags.append(node_labels[node_row[0]])

                # ? again, no idea about this
                if tmp > len(node_row):
                    node_features.append(attr)

                n_edges += node_row[1]
                # register the edges
                for edge in range(2, len(node_row)):
                    g.add_edge(j, node_row[edge])

            # ? ignore
            if node_features != []:
                node_features = np.stack(node_features)
                node_feature_flag = True
            else:
                # no node features
                node_features = None
                node_feature_flag = False

            assert len(g) == n_nodes

            # adds the graph structure, the graph label
            # and the node labels' indexes
            # ? Should be label_dict[graph_label]?
            graph_list.append(S2VGraph(g, graph_label, node_tags))

    # add labels and edge_mat
    # for each of the graphs
    for graph in graph_list:
        # create a empty neighbour list for each node
        graph.neighbors = [[] for i in range(len(graph.g))]
        # manually make an undirected graph from the structure
        for i, j in graph.g.edges():
            graph.neighbors[i].append(j)
            graph.neighbors[j].append(i)

        # calculate the degree of each node
        degree_list = []
        for i in range(len(graph.g)):
            degree_list.append(len(graph.neighbors[i]))
        graph.max_neighbor = max(degree_list)

        # ? is this redundant?
        graph.label = label_dict[graph.label]

        # create edges to make matrix
        edges = [list(pair) for pair in graph.g.edges()]
        # reciprocal
        edges.extend([[i, j] for j, i in edges])

        # generate the edge mapping with 2 lists.
        # matrix is (2,2xE),
        # 2-> node in node out
        # 2xE, double the number of edges
        graph.edge_mat = torch.LongTensor(edges).transpose(0, 1)

    # * won't be needing this
    if degree_as_tag:
        for graph in graph_list:
            graph.node_tags = list(dict(graph.g.degree).values())

    # Extracting unique tag labels
    # * used when degree_as_tag=True, useless otherwise
    tagset = set()
    for graph in graph_list:
        tagset = tagset.union(set(graph.node_tags))

    tagset = list(tagset)
    # * used when degree_as_tag=True, useless otherwise
    # * just creates {i: i} map
    # ? {node_labels.values(): node_labels.values()}
    tag2index = {tagset[i]: i for i in range(len(tagset))}

    for graph in graph_list:
        # matrix (n_nodes, n_labels)
        graph.node_features = torch.zeros(len(graph.node_tags), len(tagset))
        # * just put 1 where node has tag
        graph.node_features[
            range(len(graph.node_tags)),
            [tag2index[tag] for tag in graph.node_tags]] = 1

    print('# classes: %d' % len(label_dict))
    print('# maximum node tag: %d' % len(tagset))

    print("# data: %d" % len(graph_list))

    return graph_list, len(label_dict)


def separate_data(graph_list, seed, fold_idx):
    assert 0 <= fold_idx and fold_idx < 10, "fold_idx must be from 0 to 9."
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=seed)

    labels = [graph.label for graph in graph_list]
    idx_list = []
    for idx in skf.split(np.zeros(len(labels)), labels):
        idx_list.append(idx)
    train_idx, test_idx = idx_list[fold_idx]

    train_graph_list = [graph_list[i] for i in train_idx]
    test_graph_list = [graph_list[i] for i in test_idx]

    return train_graph_list, test_graph_list


if __name__ == "__main__":
    load_data("REDDITMULTI5K.txt", degree_as_tag=True)
