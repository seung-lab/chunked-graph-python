import numpy as np
import ipdb

split_preview = False
path_augment = False
disallow_isolating_cut = True
cg_edges = np.load('../../cg_edges.npy')
cg_affs = np.load('../../cg_affs.npy')
source_ids = np.load('../../cg_sources.npy')
sink_ids = np.load('../../cg_sinks.npy')

from pychunkedgraph.graph.cutting_scipy import LocalMincutGraphScipy
local_mincut_graph_sp = LocalMincutGraphScipy(
    cg_edges,
    cg_affs,
    source_ids,
    sink_ids,
    split_preview,
    path_augment,
    disallow_isolating_cut=disallow_isolating_cut,
)
atomic_edges_sp = local_mincut_graph_sp.compute_mincut()
ipdb.set_trace()

# from pychunkedgraph.graph.cutting import LocalMincutGraph
# local_mincut_graph = LocalMincutGraph(
#     cg_edges,
#     cg_affs,
#     source_ids,
#     sink_ids,
#     split_preview,
#     path_augment,
#     disallow_isolating_cut=disallow_isolating_cut,
# )
# atomic_edges = local_mincut_graph.compute_mincut()