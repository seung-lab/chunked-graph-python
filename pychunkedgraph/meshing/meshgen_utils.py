import os
import re
import time
from typing import Sequence
from functools import lru_cache

import numpy as np
from cloudvolume import CloudVolume, Storage

from pychunkedgraph.backend import chunkedgraph  # noqa
from pychunkedgraph.backend.utils import basetypes  # noqa


def str_to_slice(slice_str: str):
    match = re.match(r"(\d+)-(\d+)_(\d+)-(\d+)_(\d+)-(\d+)", slice_str)
    return (
        slice(int(match.group(1)), int(match.group(2))),
        slice(int(match.group(3)), int(match.group(4))),
        slice(int(match.group(5)), int(match.group(6))),
    )


def slice_to_str(slices) -> str:
    if isinstance(slices, slice):
        return "%d-%d" % (slices.start, slices.stop)
    else:
        return "_".join(map(slice_to_str, slices))


def get_chunk_bbox(cg, chunk_id: np.uint64):
    layer = cg.get_chunk_layer(chunk_id)
    chunk_block_shape = get_mesh_block_shape(cg, layer)
    bbox_start = cg.get_chunk_coordinates(chunk_id) * chunk_block_shape
    bbox_end = bbox_start + chunk_block_shape
    return tuple(slice(bbox_start[i], bbox_end[i]) for i in range(3))


def get_chunk_bbox_str(cg, chunk_id: np.uint64) -> str:
    return slice_to_str(get_chunk_bbox(cg, chunk_id))


def get_mesh_name(cg, node_id: np.uint64) -> str:
    return f"{node_id}:0:{get_chunk_bbox_str(cg, node_id)}"


@lru_cache(maxsize=None)
def get_segmentation_info(cg) -> dict:
    return cg.dataset_info


def get_mesh_block_shape(cg, graphlayer: int) -> np.ndarray:
    """
    Calculate the dimensions of a segmentation block that covers
    the same region as a ChunkedGraph chunk at layer `graphlayer`.
    """
    # Segmentation is not always uniformly downsampled in all directions.
    return cg.chunk_size * cg.fan_out ** np.max([0, graphlayer - 2])


def get_mesh_block_shape_for_mip(cg, graphlayer: int, source_mip: int) -> np.ndarray:
    """
    Calculate the dimensions of a segmentation block at `source_mip` that covers
    the same region as a ChunkedGraph chunk at layer `graphlayer`.
    """
    info = get_segmentation_info(cg)

    # Segmentation is not always uniformly downsampled in all directions.
    scale_0 = info["scales"][0]
    scale_mip = info["scales"][source_mip]
    distortion = np.floor_divide(scale_mip["resolution"], scale_0["resolution"])

    graphlayer_chunksize = cg.chunk_size * cg.fan_out ** np.max([0, graphlayer - 2])

    return np.floor_divide(
        graphlayer_chunksize, distortion, dtype=np.int, casting="unsafe"
    )


def get_downstream_multi_child_node(cg, node_id: np.uint64, stop_layer: int = 1):
    """
    Return the first descendant of `node_id` (including itself) with more than
    one child, or the first descendant of `node_id` (including itself) on or
    below layer `stop_layer`.
    """
    layer = cg.get_chunk_layer(node_id)
    if layer <= stop_layer:
        return node_id

    children = cg.get_children(node_id)
    if len(children) > 1:
        return node_id

    if not children:
        raise ValueError(f"Node {node_id} on layer {layer} has no children.")

    return get_downstream_multi_child_node(cg, children[0], stop_layer)


def get_downstream_multi_child_nodes(
    cg, node_ids: Sequence[np.uint64], require_children=True
):
    """
    Return the first descendant of `node_ids` (including themselves) with more than
    one child, or the first descendant of `node_ids` (including themselves) on or
    below layer 2.
    """
    # FIXME: Make stop_layer configurable
    stop_layer = 2

    def recursive_helper(cur_node_ids):
        cur_node_ids, unique_to_original = np.unique(cur_node_ids, return_inverse=True)
        stop_layer_mask = np.array(
            [cg.get_chunk_layer(node_id) > stop_layer for node_id in cur_node_ids]
        )
        if np.any(stop_layer_mask):
            node_to_children_dict = cg.get_children(cur_node_ids[stop_layer_mask])
            children_array = np.array(list(node_to_children_dict.values()))
            only_child_mask = np.array(
                [len(children_for_node) == 1 for children_for_node in children_array]
            )
            only_children = children_array[only_child_mask].astype(np.uint64).ravel()
            if np.any(only_child_mask):
                temp_array = cur_node_ids[stop_layer_mask]
                temp_array[only_child_mask] = recursive_helper(only_children)
                cur_node_ids[stop_layer_mask] = temp_array
        return cur_node_ids[unique_to_original]

    return recursive_helper(node_ids)


def get_highest_child_nodes_with_meshes(
    cg,
    node_id: np.uint64,
    stop_layer=2,
    start_layer=None,
    verify_existence=False,
    bounding_box=None,
    flexible_start_layer=None,
):
    if not cg.sharded_meshes:
        return children_meshes_non_sharded(
            cg,
            node_id,
            stop_layer=stop_layer,
            start_layer=start_layer,
            verify_existence=verify_existence,
            bounding_box=bounding_box,
            flexible_start_layer=flexible_start_layer,
        )
    return children_meshes_sharded(
        cg,
        node_id,
        start_layer=start_layer,
        stop_layer=stop_layer,
        verify_existence=verify_existence,
        bounding_box=bounding_box,
    )


def children_meshes_non_sharded(
    cg,
    node_id: np.uint64,
    stop_layer=2,
    start_layer=None,
    verify_existence=False,
    bounding_box=None,
    flexible_start_layer=None,
):
    if flexible_start_layer is not None:
        # Get highest children that are at flexible_start_layer or below
        # (do this because of skip connections)
        candidates = cg.get_children_at_layer(node_id, flexible_start_layer, True)
    elif start_layer is None:
        candidates = np.array([node_id], dtype=np.uint64)
    else:
        candidates = cg.get_subgraph_nodes(
            node_id,
            bounding_box=bounding_box,
            bb_is_coordinate=True,
            return_layers=[start_layer],
        )

    if verify_existence:
        valid_node_ids = []
        with Storage(cg.cv_mesh_path) as stor:
            while True:
                filenames = [get_mesh_name(cg, c) for c in candidates]

                time_start = time.time()
                existence_dict = stor.files_exist(filenames)
                print("Existence took: %.3fs" % (time.time() - time_start))

                missing_meshes = []
                for mesh_key in existence_dict:
                    node_id = np.uint64(mesh_key.split(":")[0])
                    if existence_dict[mesh_key]:
                        valid_node_ids.append(node_id)
                    else:
                        if cg.get_chunk_layer(node_id) > stop_layer:
                            missing_meshes.append(node_id)

                time_start = time.time()
                if missing_meshes:
                    candidates = cg.get_children(missing_meshes, flatten=True)
                else:
                    break
                print("ChunkedGraph lookup took: %.3fs" % (time.time() - time_start))
    else:
        valid_node_ids = candidates
    return valid_node_ids, [get_mesh_name(cg, s) for s in valid_node_ids]


def _get_json_info(cg, mesh_dir: str = None):
    from json import loads, dumps

    dataset_info = cg.dataset_info
    dummy_app_info = {"app": {"supported_api_versions": [0, 1]}}
    info = {**dataset_info, **dummy_app_info}
    if mesh_dir:
        info["mesh"] = mesh_dir

    info_str = dumps(info)
    return loads(info_str)


def children_meshes_sharded(
    cg,
    node_id: np.uint64,
    start_layer: None,
    stop_layer=2,
    verify_existence=False,
    bounding_box=None,
):
    """
    For each ID, first check for new meshes,
    If not found check initial meshes.
    """

    if not start_layer:
        start_layer = cg.get_chunk_layer(node_id)

    candidates = cg.get_subgraph_nodes(
        node_id,
        bounding_box=bounding_box,
        bb_is_coordinate=True,
        return_layers=list(range(stop_layer, start_layer)),
    )

    data_dir = "gs://seunglab2/drosophila_v0/ws_190410_FAFB_v02_ws_size_threshold_200"
    mesh_dir = "graphene_meshes"

    missing_ids = []
    dynamic_mesh_files = []

    with Storage(f"{data_dir}/{mesh_dir}/dynamic") as stor:
        time_start = time.time()
        existence_dict = stor.files_exist([get_mesh_name(cg, c) for c in candidates])
        print("Existence took: %.3fs" % (time.time() - time_start))

        for mesh_key in existence_dict:
            if existence_dict[mesh_key]:
                dynamic_mesh_files.append(mesh_key)
            else:
                missing_ids.append(np.uint64(mesh_key.split(":")[0]))

    initial_mesh_files = []
    missing_ids = np.array(missing_ids, dtype=basetypes.NODE_ID)

    cv = CloudVolume(
        f"graphene://https://localhost/segmentation/table/{cg.table_id}",
        mesh_dir=mesh_key,
        info=_get_json_info(cg, mesh_dir=mesh_dir),
    )

    layers = cg.get_chunk_layers()
    for layer_ in np.unique(layers):
        shard_infos = cv.mesh.readers[layer_].exists(  # pylint: disable=no-member
            labels=missing_ids[layers == layer_],
            path=f"{mesh_dir}/initial/{layer_}/",
            return_byte_range=True,
        )
        for val in shard_infos.values():
            path, offset, size = val
            path = path.split("initial/")[-1]
            initial_mesh_files.append(f"~{path}:{offset}:{size}")
    return candidates, dynamic_mesh_files + initial_mesh_files

