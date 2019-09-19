import random
from functools import partial
from itertools import cycle
from typing import Callable, Dict, Generator, List, Optional, Tuple, Union
from utils.generator import *
from utils.tagger import *
from utils.coloring import *

import networkx as nx
import numpy as np


def write_graphs(number_graphs: int,
                 graphs: Generator[nx.Graph, None, None],
                 tagger: Tagger,
                 filename: str = "file.txt",
                 write_features: List[str] = None) -> None:

    total_nodes = 0
    total_1s = 0
    total_graph_1s = 0
    all_1s = 0
    all_0s = 0
    avg_1s_not_all_1s = 0
    not_all_1s_size = 0

    with open(filename, 'w') as f:
        # write number of graphs
        f.write(f"{number_graphs}\n")

        for i, graph in enumerate(graphs, start=1):
            print(f"{i}/{number_graphs} graphs writen")

            graph, num_nodes, num_ones, graph_label = tagger(graph=graph)

            graph = nx.convert_node_labels_to_integers(graph)

            total_nodes += num_nodes
            total_1s += num_ones
            total_graph_1s += graph_label

            _all_1s = num_ones == len(graph)
            _all_0s = num_ones == 0

            all_1s += int(_all_1s)
            all_0s += int(_all_0s)
            avg_1s_not_all_1s += num_ones if (
                not _all_1s and not _all_0s) else 0

            not_all_1s_size += num_nodes if (
                not _all_1s and not _all_0s) else 0

            n_nodes = graph.number_of_nodes()
            label = graph.graph["label"]
            # write N_nodes in graph_i and label_i
            f.write(f"{n_nodes} {label}\n")

            # write nodes
            for node in graph.nodes(data=True):
                node_index, node_attributes = node
                edges = " ".join(map(str, list(graph[node_index].keys())))
                n_edges = len(graph[node_index])

                # writing type 1 graph
                if write_features is None:
                    f.write(
                        f"{node_attributes['color']} {n_edges} {edges}\n")

                # writing type 2 graph
                else:
                    n_features = len(write_features)
                    features = " ".join([str(node_attributes[feature])
                                         for feature in write_features])
                    assert n_features == len(features)
                    f.write(
                        f"{n_features} {features} {node_attributes['label']} {n_edges} {edges}\n")

    print(f"{total_1s}/{total_nodes} nodes were tagged 1 ({float(total_1s)/total_nodes})")
    print(f"{total_graph_1s}/{number_graphs} graphs were tagged 1 ({float(total_graph_1s)/number_graphs})")
    print(f"{all_1s}/{number_graphs} graphs with all 1 ({float(all_1s)/number_graphs})")
    print(f"{all_0s}/{number_graphs} graphs with all 0 ({float(all_0s)/number_graphs})")
    # print(f"{all_0s+all_1s}/{number_graphs} graphs with all 0 or all 1 ({float(all_0s+all_1s)/number_graphs})")
    print(f"{number_graphs-all_0s-all_1s}/{number_graphs} graphs with 0 and 1 ({float(number_graphs-all_0s-all_1s)/number_graphs})")

    if number_graphs - all_0s - all_1s > 0:
        # average number of ones per graph in graph with not all 1s
        avg_1s_not_all_1s = float(avg_1s_not_all_1s) / \
            (number_graphs - all_0s - all_1s)
        # average size of graphs with not all 1s
        not_all_1s_size = float(not_all_1s_size) / \
            (number_graphs - all_0s - all_1s)

        print(f"{avg_1s_not_all_1s}/{not_all_1s_size} avg 1s in not all 1s ({float(avg_1s_not_all_1s)/not_all_1s_size})")


def generate_dataset(filename,
                     number_graphs,
                     generator_fn,
                     n_nodes,
                     structure_fn,
                     formula,
                     seed=None,
                     number_colors=10,
                     graph_split=None,
                     color_distributions=None,
                     **kwargs):
    """
    generator_fn = empty|degree|line|random|cycle
    structure_fn = line|cycle|normal|centroid
    formula = formula{1|2|3}

    greens: Tuple[int, int]
        min and max greens

    graph_split -> [0.1, 0.3, 0.6]
    color_distributions -> {0:None, 1:[...], 2:[...]}

    kwargs:
        graph_generator:
            create_centroids: bool, default False
            centroid_only_green: bool, default True

            graph_degrees:
                degrees: List[int], default None
                variable_degree: bool, default False

            random_graph:
                p: float
                    prob of an edge in erdos
                m: int, default None
                    number of edges in "barabasi"
                    number of edges in "erdos" will be m*n_nodes
                name = "erdos"|"barabasi", default "erdos"

            cycle_graph:
                pair: bool, default True

        color_generator:
            special_line: bool
            force_color: Dict[int, Dict[int, int]]
                mapping: split -> color -> number
            force_color_position: Dict[int, Dict[int, int]]
                not yet implemented

        tag_generator:
            red_exist_green:
                n_green: int, default 1
                    number of greens to search

            color_no_connected_color:
                local_prop: List[int], default []
                    possible local properties
                global_prop: List[int], default []
                    search for global properties
                global_constraint: Dict[int, int], default {}
                    number of global properties to search
                condition: str, "and"|"or", default "and"
                    if all global properties must be satisfied or only one

            nested_property:
                nested: str, formula{1|2|3}
                    another property
                local_prop_nested: List[int], default []
                nested_constraint: int, default 1
                    how many properties must be satisfied that are not from neighbors
                self_satisfy: bool, default True
    """

    random.seed(seed)
    np.random.seed(seed)
    kwargs["seed"] = seed

    min_nodes, max_nodes = n_nodes

    tagger = Tagger(formula, **kwargs)
    generator = graph_generator(generator_fn=generator_fn,
                                min_nodes=min_nodes,
                                max_nodes=max_nodes,
                                **kwargs)
    color_graphs = color_generator(graph_generator=generator,
                                   number_graphs=number_graphs,
                                   min_nodes=min_nodes,
                                   max_nodes=max_nodes,
                                   graph_split=graph_split,
                                   color_distributions=color_distributions,
                                   structure_fn=structure_fn,
                                   n_colors=number_colors,
                                   **kwargs)

    if "cycle" in filename:
        file_name = f"data/{formula}/{filename}-{number_graphs}-{min_nodes}-{max_nodes}-{kwargs['m']}.txt"
    elif "asd" in filename:
        file_name = f"data/{formula}/{filename}.txt"
    else:
        file_name = f"data/{formula}/{filename}-{number_graphs}-{min_nodes}-{max_nodes}.txt"

    write_graphs(number_graphs=number_graphs,
                 graphs=color_graphs,
                 tagger=tagger,
                 filename=file_name,
                 write_features=["color"])


if __name__ == "__main__":
    # TODO: implement manual limit to number of nodes with each color
    """
    formula1 -> x in G, red(x) and exist_N y in G, such that green(y)
    formula3 -> x in G, R_1(x) and
        (exist_N_1 y_1 in G, such that G_1(y_1) AND|OR
         exist_N_2 y_2 in G, such that G_2(y_2) AND|OR ...)
    formula4 -> x in G, R_1(x) and Exists N nodes that are not in Neigh(x) that satisfiy property Y
    """

    _tagger_fn = "formula4"
    _name = "barabasi"
    _data_name = f"random-{_name}"
    _m = 2

    generate_dataset(f"asd-{_data_name}",
                     number_graphs=1000,
                     # empty|degree|line|random|cycle
                     generator_fn=_data_name.split("-")[0],
                     n_nodes=(50, 50),
                     # line|cycle|normal|centroid
                     structure_fn="normal",
                     # formula{1|2|3}
                     formula=_tagger_fn,
                     seed=None,
                     number_colors=5,
                     # global, tuple
                     greens=(12, 12),
                     # random
                     name=_name,
                     m=_m,
                     # centroid
                     create_centroids=False,
                     centroids=(2, 2),
                     nodes_per_centroid=(20, 20),
                     centroid_connectivity=0.5,
                     centroid_extra=None,  # {},
                     centroid_only_green=True,
                     # tagger
                     # formula 1
                     n_green=1,
                     # formula 3
                     local_prop=[],
                     global_prop=[0],
                     global_constraint={0: 12},
                     condition="and",
                     # formula 4
                     nested="formula3",
                     local_prop_nested=[],
                     nested_constraint=10,
                     self_satisfy=False)

    # test_dataset(
    #     name=_data_name,
    #     tagger_fn=_tagger_fn,
    #     seed=None,
    #     n_colors=5,
    #     number_of_graphs=500,
    #     n_min=50,
    #     n_max=100,
    #     random_degrees=True,
    #     min_degree=0,
    #     max_degree=2,
    #     no_green=False,
    #     special_line=True,
    #     edges=0.025,
    #     split_line=_split_line,
    #     m=_m,
    #     force_green=3,
    #     two_color=True,
    #     # tagger
    #     # formula 1
    #     n_green=1,
    #     # formula 3
    #     local_prop=[1],
    #     global_prop=[0],
    #     global_constraint={0: 1},
    #     condition="or")

    # test_dataset(
    #     name=_data_name,
    #     tagger_fn=_tagger_fn,
    #     seed=None,
    #     n_colors=5,
    #     number_of_graphs=500,
    #     n_min=100,
    #     n_max=200,
    #     random_degrees=True,
    #     min_degree=0,
    #     max_degree=_prop,
    #     no_green=False,
    #     special_line=True,
    #     edges=0.025,
    #     split_line=_split_line,
    #     m=_m,
    #     force_green=3,
    #     two_color=True,
    #     # tagger
    #     # formula 1
    #     n_green=1,
    #     # formula 3
    #     local_prop=[1],
    #     global_prop=[0],
    #     global_constraint={0: 1},
    #     condition="or")
