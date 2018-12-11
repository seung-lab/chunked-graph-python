from pychunkedgraph.backend.chunkedgraph import ChunkedGraph
import numpy as np
from graph_tool import all as gt
import igraph as ig
import networkx as nx

cg = ChunkedGraph("pinky100_sv16")
root_id = np.uint64(648518346349498239)
edges, affinities, _ = cg.get_subgraph_edges(root_id, verbose=True)
edges.

graph_gt = gt.Graph(directed=False)
vertex_map = graph_gt.add_edge_list(edges, hashed=True)
cap = graph_gt.new_edge_property("float", vals=affinities)
graph_gt.edge_properties["cap"] = cap

mc, part = gt.flow.boykov_kolmogorov_max_flow(graph_gt, cap)