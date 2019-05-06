import numpy as np
from pychunkedgraph.backend import chunkedgraph, chunkedgraph_utils

import cloudvolume


def calc_n_layers(ws_cv, chunk_size, fan_out):
    bbox = np.array(ws_cv.bounds.to_list()).reshape(2, 3)
    n_chunks = ((bbox[1] - bbox[0]) / chunk_size).astype(np.int)
    n_layers = int( np.ceil(chunkedgraph_utils.log_n(np.max(n_chunks), fan_out))) + 2
    return n_layers


def initialize_chunkedgraph(cg_table_id, ws_cv_path, chunk_size, size, cg_mesh_dir,
                            s_bits_atomic_layer=None, n_bits_root_counter=8,
                            fan_out=2, instance_id=None, project_id=None):
    """ Initalizes a chunkedgraph on BigTable

    :param cg_table_id: str
        name of chunkedgraph
    :param ws_cv_path: str
        path to watershed segmentation on Google Cloud
    :param chunk_size: np.ndarray
        array of three ints
    :param size: np.ndarray
        array of three ints
    :param cg_mesh_dir: str
        mesh folder name
    :param s_bits_atomic_layer: int or None
        number of bits for each x, y and z on the lower layer
    :param n_bits_root_counter: int or None
        number of bits for counters in root layer
    :param fan_out: int
        fan out of chunked graph (2 == Octree)
    :param instance_id: str
        Google instance id
    :param project_id: str
        Google project id
    :return: ChunkedGraph
    """
    ws_cv = cloudvolume.CloudVolume(ws_cv_path)

    n_layers_agg = calc_n_layers(ws_cv, chunk_size, fan_out=2)

    if size is not None:
        size = np.array(size)
        for i in range(len(ws_cv.info['scales'])):
            original_size = ws_cv.info['scales'][i]['size']
            size = np.min([size, original_size], axis=0)
            ws_cv.info['scales'][i]['size'] = [int(x) for x in size]
            size[:-1] //= 2

    n_layers_cg = calc_n_layers(ws_cv, chunk_size, fan_out=fan_out)

    dataset_info = ws_cv.info
    dataset_info["mesh"] = cg_mesh_dir
    dataset_info["data_dir"] = ws_cv_path
    dataset_info["graph"] = {"chunk_size": [int(s) for s in chunk_size]}

    kwargs = {"table_id": cg_table_id,
              "chunk_size": chunk_size,
              "fan_out": np.uint64(fan_out),
              "n_layers": np.uint64(n_layers_cg),
              "dataset_info": dataset_info,
              "s_bits_atomic_layer": s_bits_atomic_layer,
              "n_bits_root_counter": n_bits_root_counter,
              "is_new": True}

    if instance_id is not None:
        kwargs["instance_id"] = instance_id

    if project_id is not None:
        kwargs["project_id"] = project_id

    cg = chunkedgraph.ChunkedGraph(**kwargs)

    return cg, n_layers_agg
