from typing import Dict
from typing import Tuple

import numpy as np

from .types import ChunkTask
from .manager import IngestionManager
from .backward_compat import get_chunk_data as get_chunk_data_old_format
from .ran_agglomeration import read_raw_edge_data
from .ran_agglomeration import read_raw_agglomeration_data
from ..io.edges import get_chunk_edges
from ..io.components import get_chunk_components


def create_atomic_chunk_helper(task: ChunkTask, imanager: IngestionManager):
    """Helper to queue atomic chunk task."""
    chunk_edges_all, mapping = _get_atomic_chunk_data(imanager, task.coords)
    ids, affs, areas, isolated = get_chunk_data_old_format(chunk_edges_all, mapping)
    imanager.cg.add_atomic_edges_in_chunks(
        ids, affs, areas, isolated, time_stamp=imanager.cg_meta.graph_config.time_stamp
    )
    return task


def create_parent_chunk_helper(task: ChunkTask, imanager: IngestionManager):
    """Helper to queue parent chunk task."""
    imanager.cg.add_layer(
        task.layer,
        task.children_coords,
        time_stamp=imanager.cg_meta.graph_config.time_stamp,
    )
    return task


def _get_atomic_chunk_data(
    imanager: IngestionManager, coord: np.ndarray
) -> Tuple[Dict, Dict]:
    """
    Helper to read either raw data or processed data
    If reading from raw data, save it as processed data
    """
    chunk_edges = (
        read_raw_edge_data(imanager, coord)
        if imanager.cg_meta.data_source.use_raw_edges
        else get_chunk_edges(imanager.cg_meta.data_source.edges, [coord])
    )
    mapping = (
        read_raw_agglomeration_data(imanager, coord)
        if imanager.cg_meta.data_source.use_raw_components
        else get_chunk_components(imanager.cg_meta.data_source.components, coord)
    )
    return chunk_edges, mapping
