import cloudvolume
import fastremap
import numpy as np

from multiwrapper import multiprocessing_utils as mu

from pychunkedgraph.backend import chunkedgraph


def get_remapped_block(cv_in, cg, bounding_box, timestamp=None):
    ws = cv_in.download(cloudvolume.Bbox(*bounding_box))

    sv_ids = np.unique(ws)
    sv_ids = sv_ids[sv_ids != 0]

    if len(sv_ids) == 0:
        return None

    root_ids = cg.get_roots(sv_ids, time_stamp=timestamp)
    lookup_table = dict(zip(sv_ids, root_ids))
    lookup_table[0] = 0
    remapped_seg = fastremap.remap(ws, lookup_table)

    return remapped_seg


def _process_blocks(args):
    serialized_cg_info, cv_out_path, block_coordinates, timestamp, block_size, mip = args

    cg = chunkedgraph.ChunkedGraph(**serialized_cg_info)
    cv_in = cloudvolume.CloudVolume(cg._cv_path, mip=mip, bounded=False)
    cv_out = cloudvolume.CloudVolume(cv_out_path, mip=mip, bounded=False,
                                     non_aligned_writes=True)

    for block_coordinate in block_coordinates:
        bbox = [block_coordinate, block_coordinate + block_size]

        remapped_seg = get_remapped_block(cv_in, cg, bbox, timestamp=timestamp)

        if remapped_seg is None:
            continue

        cv_out[bbox[0][0]: bbox[1][0],
               bbox[0][1]: bbox[1][1],
               bbox[0][2]: bbox[1][2]] = remapped_seg

        print(f"written {bbox}")


def process_dataset(cg, cv_out_path, block_size=[512, 512, 128], mip=0,
                    timestamp=None, n_threads=64):
    cv_out = cloudvolume.CloudVolume(cv_out_path, mip=mip)

    block_size = np.array(block_size)
    bounds = np.array(cv_out.bounds.to_list()).reshape(2, 3).astype(np.float)
    n_blocks = np.ceil((bounds[1] - bounds[0]) / block_size).astype(np.int)

    block_coords = []
    for i_x in range(n_blocks[0]):
        for i_y in range(n_blocks[1]):
            for i_z in range(n_blocks[2]):
                block_coords.append([i_x, i_y, i_z])

    block_coords = np.array(block_coords) * block_size + bounds[0]
    block_coords = block_coords.astype(np.int)
    block_coords = block_coords[np.random.choice(np.arange(len(block_coords)),
                                                 len(block_coords),
                                                 replace=False)]

    block_coord_blocks = np.array_split(block_coords, n_threads * 3)

    cg_serialized_info = cg.get_serialized_info()

    if n_threads > 1:
        del cg_serialized_info["credentials"]

    multi_args = []
    for block_coord_block in block_coord_blocks:
        multi_args.append([cg_serialized_info, cv_out_path, block_coord_block,
                           timestamp, block_size, mip])

    if n_threads == 1:
        results = mu.multiprocess_func(_process_blocks,
                                       multi_args, n_threads=n_threads,
                                       verbose=False, debug=n_threads == 1)
    else:
        results = mu.multisubprocess_func(_process_blocks,
                                          multi_args, n_threads=n_threads)
