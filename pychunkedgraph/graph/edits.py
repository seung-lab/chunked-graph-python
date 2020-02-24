import datetime
import numpy as np
from typing import Dict
from typing import List
from typing import Tuple
from typing import Iterable
from typing import Sequence
from collections import defaultdict

from . import cache
from . import types
from .utils import basetypes
from .utils import flatgraph
from .utils.context_managers import TimeIt
from .connectivity.nodes import edge_exists
from .edges.utils import filter_min_layer_cross_edges
from .edges.utils import concatenate_cross_edge_dicts
from .edges.utils import merge_cross_edge_dicts_multiple
from ..utils.general import in2d
from ..utils.general import reverse_dictionary


"""
TODO
1. get split working
2. handle fake edges 
3. unit tests, edit old and create new
4. split merge manual tests
5. performance
6. meshing
7. ingest instructions, pinky test run


Their children might be "too much" due to the split; even within one chunk. How do you deal with that?

a good way to test this is to check all intermediate nodes from the component before the split and then after the split. Basically, get all childrens in all layers of the one component before and the (hopefully) two components afterwards. Check (1) are all intermediate nodes from before in a list after and (2) do all intermediate nodes appear exactly one time after the split (aka is there overlap between the resulting components). (edited) 

for (2) Overlap can be real but then they have to be exactly the same. In that case the removed edges did not split the component in two

"""


def _analyze_atomic_edges(
    cg, atomic_edges: Iterable[np.ndarray]
) -> Tuple[Iterable, Dict]:
    """
    Determine if atomic edges are within the chunk.
    If not, they are cross edges between two L2 IDs in adjacent chunks.
    Returns edges between L2 IDs and atomic cross edges.
    """
    nodes = np.unique(atomic_edges)
    parents = cg.get_parents(nodes)
    parents_d = dict(zip(nodes, parents))
    edge_layers = cg.get_cross_chunk_edges_layer(atomic_edges)
    mask = edge_layers == 1

    # initialize with in-chunk edges
    with TimeIt("get_parents edges"):
        parent_edges = [
            [parents_d[edge_[0]], parents_d[edge_[1]]] for edge_ in atomic_edges[mask]
        ]

    # cross chunk edges
    atomic_cross_edges_d = {}
    for edge, layer in zip(atomic_edges[~mask], edge_layers[~mask]):
        parent_1 = parents_d[edge[0]]
        parent_2 = parents_d[edge[1]]
        atomic_cross_edges_d[parent_1] = {layer: [edge]}
        atomic_cross_edges_d[parent_2] = {layer: [edge[::-1]]}
        parent_edges.append([parent_1, parent_1])
        parent_edges.append([parent_2, parent_2])
    return (parent_edges, atomic_cross_edges_d)


def _get_all_old_ids(cg, l2ids: np.ndarray) -> np.ndarray:
    """
    Parents of IDs affected by an edit.
    They need to be excluded when building new hierarchy.
    """
    layer = 3
    old_ids = [l2ids]
    parents = l2ids.copy()
    mask = cg.get_chunk_layers(parents) < layer
    while np.any(mask):
        parents[mask] = cg.get_roots(parents[mask], stop_layer=layer)
        old_ids.append(parents.copy())
        layer += 1
        mask = cg.get_chunk_layers(parents) < layer
    return np.unique(np.concatenate(old_ids))


def add_edges(
    cg,
    *,
    atomic_edges: Iterable[np.ndarray],
    operation_id: np.uint64 = None,
    source_coords: Sequence[np.uint64] = None,
    sink_coords: Sequence[np.uint64] = None,
    time_stamp: datetime.datetime = None,
):
    """
    Problem: Update parent and children of the new level 2 id
    For each layer >= 2
        get cross edges
        get parents
            get children
        above children + new ID will form a new component
        update parent, former parents and new parents for all affected IDs
    """
    edges, l2_atomic_cross_edges_d = _analyze_atomic_edges(cg, atomic_edges)
    l2ids = np.unique(edges)
    old_ids = _get_all_old_ids(cg, l2ids)

    # setup relevant children and atomic cross edges
    atomic_children_d = cg.get_children(l2ids)
    atomic_cross_edges_d = merge_cross_edge_dicts_multiple(
        cg.get_atomic_cross_edges(l2ids), l2_atomic_cross_edges_d
    )

    graph, _, _, graph_node_ids = flatgraph.build_gt_graph(edges, make_directed=True)
    ccs = flatgraph.connected_components(graph)
    new_l2_ids = []
    for cc in ccs:
        l2ids_ = graph_node_ids[cc]
        new_id = cg.id_client.create_node_id(cg.get_chunk_id(l2ids_[0]))
        cache.CHILDREN[new_id] = np.concatenate(
            [atomic_children_d[l2id] for l2id in l2ids_]
        )
        cache.ATOMIC_CX_EDGES[new_id] = concatenate_cross_edge_dicts(
            [atomic_cross_edges_d[l2id] for l2id in l2ids_]
        )
        cache.update(cache.PARENTS, cache.CHILDREN[new_id], new_id)
        new_l2_ids.append(new_id)

    create_parents = CreateParentNodes(
        cg,
        new_l2_ids=new_l2_ids,
        old_ids=old_ids,
        operation_id=operation_id,
        time_stamp=time_stamp,
    )
    return create_parents.run()


def _process_l2_agglomeration(
    agg: types.Agglomeration,
    removed_edges: np.ndarray,
    atomic_cross_edges_d: Dict[int, np.ndarray],
):
    """
    For a given L2 id, remove given edges
    and calculate new connected components.
    """
    chunk_edges = agg.in_edges.get_pairs()
    cross_edges = np.concatenate([*atomic_cross_edges_d[agg.node_id].values()])
    chunk_edges = chunk_edges[~in2d(chunk_edges, removed_edges)]
    cross_edges = cross_edges[~in2d(cross_edges, removed_edges)]

    isolated_ids = agg.supervoxels[~np.in1d(agg.supervoxels, chunk_edges)]
    isolated_edges = np.column_stack((isolated_ids, isolated_ids))
    graph, _, _, unique_graph_ids = flatgraph.build_gt_graph(
        np.concatenate([chunk_edges, isolated_edges]), make_directed=True
    )
    return flatgraph.connected_components(graph), unique_graph_ids, cross_edges


def _filter_component_cross_edges(
    cc_ids: np.ndarray, cross_edges: np.ndarray, cross_edge_layers: np.ndarray
) -> Dict[int, np.ndarray]:
    """
    Filters cross edges for a connected component `cc_ids`
    from `cross_edges` of the complete chunk.
    """
    mask = np.in1d(cross_edges[:, 0], cc_ids)
    cross_edges_ = cross_edges[mask]
    cross_edge_layers_ = cross_edge_layers[mask]
    edges_d = {}
    for layer in np.unique(cross_edge_layers_):
        edge_m = cross_edge_layers_ == layer
        _cross_edges = cross_edges_[edge_m]
        if _cross_edges.size:
            edges_d[layer] = _cross_edges
    return edges_d


def remove_edges(
    cg,
    *,
    atomic_edges: Iterable[np.ndarray],
    l2id_agglomeration_d: Dict,
    operation_id: basetypes.OPERATION_ID = None,
    time_stamp: datetime.datetime = None,
):
    cache.clear()
    cg.cache = cache.CacheService(cg)
    edges, _ = _analyze_atomic_edges(cg, atomic_edges)
    l2ids = np.unique(edges)
    print("l2ids", l2ids)
    old_ids = _get_all_old_ids(cg, l2ids)
    l2id_chunk_id_d = dict(zip(l2ids, cg.get_chunk_ids_from_node_ids(l2ids)))
    atomic_cross_edges_d = cg.get_atomic_cross_edges(l2ids)

    new_old_id_d = defaultdict(list)
    old_hierarchy_d = {id_: {2: id_} for id_ in l2ids}
    for id_ in l2ids:
        old_hierarchy_d[id_].update(cg.get_all_parents_dict(id_))

    # This view of the to be removed edges helps us to
    # compute the mask of retained edges in chunk
    removed_edges = np.concatenate([atomic_edges, atomic_edges[:, ::-1]], axis=0)
    new_l2_ids = []
    for id_ in l2ids:
        l2_agg = l2id_agglomeration_d[id_]
        ccs, unique_graph_ids, cross_edges = _process_l2_agglomeration(
            l2_agg, removed_edges, atomic_cross_edges_d
        )
        cross_edge_layers = cg.get_cross_chunk_edges_layer(cross_edges)
        new_parent_ids = cg.id_client.create_node_ids(
            l2id_chunk_id_d[l2_agg.node_id], len(ccs)
        )
        for i_cc, cc in enumerate(ccs):
            new_id = new_parent_ids[i_cc]
            cache.CHILDREN[new_id] = unique_graph_ids[cc]
            cache.ATOMIC_CX_EDGES[new_id] = _filter_component_cross_edges(
                cache.CHILDREN[new_id], cross_edges, cross_edge_layers
            )
            cache.update(cache.PARENTS, cache.CHILDREN[new_id], new_id)
            new_l2_ids.append(new_id)
            new_old_id_d[new_id].append(id_)

    create_parents = CreateParentNodes(
        cg,
        new_l2_ids=new_l2_ids,
        old_ids=old_ids,
        old_hierarchy_d=old_hierarchy_d,
        new_old_id_d=new_old_id_d,
        operation_id=operation_id,
        time_stamp=time_stamp,
    )
    return atomic_edges, create_parents.run()


class CreateParentNodes:
    def __init__(
        self,
        cg,
        *,
        new_l2_ids: Iterable,
        old_ids: np.ndarray,
        old_hierarchy_d: Dict[np.uint64, Dict[int, np.uint64]] = None,
        new_old_id_d: Dict[np.uint64, Iterable[np.uint64]] = None,
        operation_id: basetypes.OPERATION_ID,
        time_stamp: datetime.datetime,
    ):
        self.cg = cg
        self.new_l2_ids = new_l2_ids
        self.old_ids = old_ids
        self.operation_id = operation_id
        self.old_hierarchy_d = old_hierarchy_d
        self.new_old_id_d = new_old_id_d
        self.time_stamp = time_stamp
        self._layer_ids_d = defaultdict(list)  # new IDs in each layer
        self._cross_edges_d = {}
        self._done = set()

    def _create_new_sibling(self, child_id, sibling_layer) -> basetypes.NODE_ID:
        """
        `child_id` child ID of the missing sibling
        `layer` layer at which the missing sibling needs to be created
        """
        # current parent skipped this layer, so it would be grand parent
        grandpa_id = self.cg.get_parent(child_id)
        new_sibling_id = self.cg.id_client.create_node_id(
            self.cg.get_parent_chunk_id(child_id, sibling_layer)
        )

        old_children = self.cg.get_children(grandpa_id)
        cache.CHILDREN[grandpa_id] = np.setdiff1d(
            old_children, [child_id], assume_unique=True,
        )
        cache.update(
            cache.PARENTS, cache.CHILDREN[grandpa_id], grandpa_id,
        )
        cache.CHILDREN[new_sibling_id] = np.array([child_id], dtype=basetypes.NODE_ID)
        cache.PARENTS[child_id] = new_sibling_id
        # print("new_sibling_id", child_id, new_sibling_id)
        return new_sibling_id

    def _handle_missing_siblings(self, layer, new_id_ce_siblings) -> np.ndarray:
        """Create new sibling when a new ID has none because of skip connections."""
        mask = self.cg.get_chunk_layers(new_id_ce_siblings) < layer
        missing = new_id_ce_siblings[mask]
        for id_ in missing:
            self._layer_ids_d[layer].append(self._create_new_sibling(id_, layer))
        new_id_ce_siblings[mask] = self.cg.get_parents(missing)
        return new_id_ce_siblings

    def _get_all_new_sibling_siblings(
        self, layer: int, ce_siblings: np.ndarray
    ) -> np.ndarray:
        new_siblings = np.intersect1d(
            ce_siblings, self._layer_ids_d[layer], assume_unique=True
        )
        all_siblings = [types.empty_1d]
        for sibling in new_siblings:
            all_siblings.append(self._cross_edges_d[sibling][layer][:, 1])
        ce_siblings = np.unique(np.concatenate([*all_siblings, ce_siblings]))
        return self._handle_missing_siblings(layer, ce_siblings)

    def _create_parent(
        self,
        new_id: basetypes.NODE_ID,
        layer: int,
        ce_layer: int,
        ce_siblings: np.ndarray,
    ) -> None:
        """Helper function."""
        print()
        print("-" * 100)
        print("new_id", new_id, ce_layer, ce_siblings)
        if new_id in self._done:
            return  # parent already updated
        chunk_id = self.cg.get_parent_chunk_id
        if ce_layer > layer:
            # skip connection
            parent_id = self.cg.id_client.create_node_id(chunk_id(new_id, ce_layer))
            cache.CHILDREN[parent_id] = np.array([new_id], dtype=basetypes.NODE_ID)
            self._layer_ids_d[ce_layer].append(parent_id)
        else:
            parent_id = self.cg.id_client.create_node_id(chunk_id(new_id, layer + 1))
            ce_siblings = self._get_all_new_sibling_siblings(layer, ce_siblings)
            # siblings that are also new IDs
            common = np.intersect1d(
                ce_siblings, self._layer_ids_d[layer], assume_unique=True
            )

            # they do not have parents yet so exclude them
            siblings = self._get_all_siblings(
                new_id,
                parent_id,
                layer,
                np.setdiff1d(ce_siblings, common, assume_unique=True),
            )

            cache.CHILDREN[parent_id] = np.unique(
                np.concatenate([[new_id], common, siblings])
            )
            self._layer_ids_d[layer + 1].append(parent_id)
            self._done.update(  # flag children that are new as done
                np.intersect1d(
                    cache.CHILDREN[parent_id],
                    self._layer_ids_d[layer],
                    assume_unique=True,
                )
            )
        cache.update(cache.PARENTS, cache.CHILDREN[parent_id], parent_id)
        self._done.add(new_id)

    def _get_components(self, layer, new_ids):
        print("new_ids", new_ids)
        old_ids = [self.new_old_id_d[id_] for id_ in new_ids]
        old_ids = np.unique(np.array(old_ids, dtype=basetypes.NODE_ID))
        old_new_id_d = reverse_dictionary(self.new_old_id_d)

        parents = self.cg.get_parents(old_ids)
        node_children_d = self.cg.get_children(np.unique(parents))
        siblings = defaultdict(list)
        for new_id in new_ids:
            print()
            print("************** new_id", new_id)
            siblings[new_id].append(types.empty_1d)
            parents = [self.cg.get_parent(id_) for id_ in self.new_old_id_d[new_id]]
            for parent in parents:
                siblings[new_id].append(node_children_d[parent])
            siblings[new_id] = np.concatenate(siblings[new_id])
            print("siblings b", siblings[new_id])
            old_ids_ = self.new_old_id_d[new_id]
            mask = np.in1d(siblings[new_id], old_ids_, assume_unique=True)
            siblings[new_id][mask] = np.array([old_new_id_d[id_] for id_ in old_ids_])
            print("siblings a", siblings[new_id])

        # TODO
        # keep track of old IDs
        # merge - one new ID has 2 old IDs
        # split - two new IDs have the same old ID
        # get parents of old IDs, their children are the siblings
        # those siblings include old IDs, replace with new
        # get cross edges of all, find connected components
        # handle skip connection

    def run(self) -> Iterable:
        """
        After new level 2 IDs are created, create parents in higher layers.
        Cross edges are used to determine existing siblings.
        """
        self._get_components(2, self.new_l2_ids)
        return
        self._layer_ids_d[2] = self.new_l2_ids
        for current_layer in range(2, self.cg.meta.layer_count):
            print("*" * 100)
            print("layer", current_layer, self._layer_ids_d[current_layer])
            if len(self._layer_ids_d[current_layer]) == 0:
                continue

            new_ids = np.array(self._layer_ids_d[current_layer], basetypes.NODE_ID)
            cached = np.fromiter(self._cross_edges_d.keys(), dtype=basetypes.NODE_ID)
            not_cached = new_ids[~np.in1d(new_ids, cached)]
            self._cross_edges_d.update(
                self.cg.get_cross_chunk_edges(not_cached, uplift=False)
            )
        # return self._done, self._layer_ids_d
        return self._layer_ids_d[self.cg.meta.layer_count]
