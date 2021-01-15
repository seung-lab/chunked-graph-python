import fastremap
import numpy as np
from itertools import combinations, chain
from graph_tool import Graph
from graph_tool import topology, search


def build_gt_graph(
    edges, weights=None, is_directed=True, make_directed=False, hashed=False
):
    """ Builds a graph_tool graph
    :param edges: n x 2 numpy array
    :param weights: numpy array of length n
    :param is_directed: bool
    :param make_directed: bool
    :param hashed: bool
    :return: graph, capacities
    """
    edges = np.array(edges, np.uint64)
    if weights is not None:
        assert len(weights) == len(edges)
        weights = np.array(weights)

    unique_ids, edges = np.unique(edges, return_inverse=True)
    edges = edges.reshape(-1, 2)

    edges = np.array(edges)

    if make_directed:
        is_directed = True
        edges = np.concatenate([edges, edges[:, [1, 0]]])

        if weights is not None:
            weights = np.concatenate([weights, weights])

    weighted_graph = Graph(directed=is_directed)
    weighted_graph.add_edge_list(edge_list=edges, hashed=hashed)

    if weights is not None:
        cap = weighted_graph.new_edge_property("float", vals=weights)
    else:
        cap = None
    return weighted_graph, cap, edges, unique_ids


def remap_ids_from_graph(graph_ids, unique_ids):
    return unique_ids[graph_ids]


def connected_components(graph):
    """ Computes connected components of graph_tool graph
    :param graph: graph_tool.Graph
    :return: np.array of len == number of nodes
    """
    assert isinstance(graph, Graph)

    cc_labels = topology.label_components(graph)[0].a

    if len(cc_labels) == 0:
        return []

    idx_sort = np.argsort(cc_labels)
    _, idx_start = np.unique(cc_labels[idx_sort], return_index=True)

    return np.split(idx_sort, idx_start[1:])


def team_paths_all_to_all(graph, capacity, team_vertex_ids):
    """ Finds all paths between pairs of points on a source/sink team.
    """
    dprop = capacity.copy()
    # Use inverse affinity as the distance between vertices.
    dprop.a = 1/(dprop.a + np.finfo(np.float64).eps)

    paths_v = []
    paths_e = []
    cache_pred_map = {}
    for i1, i2 in combinations(team_vertex_ids, 2):
        pred_map = cache_pred_map.get(i1, None)
        if pred_map is None:
            _, pred_map = search.dijkstra_search(
                graph, dprop, source=graph.vertex(i1))
            cache_pred_map[i1] = pred_map
            pop_keys = []
            for k in cache_pred_map.keys():
                if k != i1:
                    pop_keys.append(k)
            for k in pop_keys:
                cache_pred_map.pop(k)

        path_v, path_e = topology.shortest_path(
            graph, graph.vertex(i1), graph.vertex(i2), pred_map=pred_map)
        paths_v.append(path_v)
        paths_e.append(path_e)
    return paths_v, paths_e


def neighboring_edges(graph, vertex_id):
    """ Returns vertex and edge lists of a seed vertex, in the same format as team_paths_all_to_all.
    """
    add_v = []
    add_e = []
    v0 = graph.vertex(vertex_id)
    neibs = v0.out_neighbors()
    for v in neibs:
        add_v.append(v)
        add_e.append(graph.edge(v, v0))
    return [add_v], [add_e]


def remove_overlapping_edges(paths_v_s, paths_e_s, paths_v_y, paths_e_y):
    """Remove vertices that are in the paths from both teams
    """
    inds_s = np.unique([int(v) for v in chain.from_iterable(paths_v_s)])
    inds_y = np.unique([int(v) for v in chain.from_iterable(paths_v_y)])
    intersect_nodes = np.intersect1d(inds_s, inds_y)
    if len(intersect_nodes) == 0:
        return paths_e_s, paths_e_y, False
    else:
        path_e_s_out = [[e for e in chain.from_iterable(paths_e_s) if not np.any(
            np.isin([int(e.source()), int(e.target())], intersect_nodes))]]
        path_e_y_out = [[e for e in chain.from_iterable(paths_e_y) if not np.any(
            np.isin([int(e.source()), int(e.target())], intersect_nodes))]]
        return path_e_s_out, path_e_y_out, True


def check_connectedness(vertices, edges, expected_number=1):
    """Returns True if the augmenting edges still form a single connected component
    """
    paths_inds = np.unique([int(v) for v in chain.from_iterable(vertices)])
    edge_list_inds = np.array([[int(e.source()), int(e.target())]
                               for e in chain.from_iterable(edges)])

    rmap = {v: ii for ii, v in enumerate(paths_inds)}
    edge_list_remap = fastremap.remap(edge_list_inds, rmap)

    g2 = Graph(directed=False)
    g2.add_vertex(n=len(paths_inds))
    g2.add_edge_list(edge_list_remap)

    _, count = topology.label_components(g2)
    return len(count) == expected_number


def reverse_edge(graph, edge):
    """Returns the complementary edge
    """
    return graph.edge(edge.target(), edge.source())


def adjust_affinities(graph, capacity, paths_e, value=np.finfo(np.float32).max):
    """Set affinity of a subset of paths to a particular value (typically the largest double).
    """
    capacity = capacity.copy()
    for pair_path in paths_e:
        for edge in pair_path:
            capacity[edge] = value
            # Capacity is a symmetric directed network
            capacity[reverse_edge(graph, edge)] = value
    return capacity
