from pychunkedgraph.meshing.meshgen import remeshing, mesh_segid_thread
from pychunkedgraph.backend.chunkedgraph import ChunkedGraph
import pychunkedgraph
import cloudvolume
import numpy as np
import collections
import os
import multiwrapper.multiprocessing_utils as mu
from analysisdatalink.datalink_ext import AnalysisDataLinkExt as AnalysisDataLink

dataset_name = 'pinky100'
mat_version = 175
HOME = os.path.expanduser("~")
orig_cv_path = 'https://storage.googleapis.com/neuroglancer/nkem/pinky100_v0/ws/lost_no-random/bbox1_0'
cv_path = f'file://{HOME}/friday_harbor_v2/friday_harbor_pinky100_sv16/'
cv_mesh_dir = "friday_harbor_meshes"
cg = ChunkedGraph("pinky100_sv16")
stop_layer=2
mip = 2
n_threads = 64
n_jobs = max(n_threads * 3, 100)
# seg_id = 648518346342801110

dl = AnalysisDataLink(dataset_name, mat_version, sqlalchemy_database_uri=os.environ['MATERIALIZATION_POSTGRES_URI'], verbose=False)
soma_df = dl.query_cell_types('soma_valence_v2',  cell_type_include_filter=['e','i'], exclude_zero_root_ids=False)

# make a proper cloud volume at this path
orig_cv = cloudvolume.CloudVolume(orig_cv_path)
info = orig_cv.info
info['mesh']=cv_mesh_dir
new_cv = cloudvolume.CloudVolume(cv_path, info=info)
new_cv.commit_info()

# setup the multiprocessing
# seg_ids = [648518346342801110]
seg_ids = soma_df.pt_root_id.map(int).values

l2_chunk_dict = collections.defaultdict(list)

n_lvl2_ids = 0
for seg_id in seg_ids:
    lvl2_ids = cg.get_subgraph_nodes(seg_id, return_layers=[2])
    n_lvl2_ids += len(lvl2_ids)

    for lvl2_id in lvl2_ids:
        chunk_id = cg.get_chunk_id(lvl2_id)
        l2_chunk_dict[chunk_id].append(lvl2_id)

cg_info = cg.get_serialized_info()
del cg_info["credentials"]

print(f"Number of level 2 node ids:{n_lvl2_ids}")
print(f"Number of level 2 chunk ids:{len(l2_chunk_dict)}")

margs = []
for chunk_ids in np.array_split(list(l2_chunk_dict.keys()), n_jobs):
    lvl2_node_ids = []

    for chunk_id in chunk_ids:
        lvl2_node_ids.extend(l2_chunk_dict[chunk_id])

    margs.append((cg_info, cv_path, cv_mesh_dir, lvl2_node_ids, stop_layer, mip))

mu.multisubprocess_func(pychunkedgraph.meshing.meshgen.mesh_segid_thread,
                        margs, n_threads=n_threads)

# lvl2_ids = cg.get_subgraph_nodes(seg_id, return_layers=[2])
# remeshing(cg, lvl2_ids, stop_layer=9, cv_path=cv_path, cv_mesh_dir='meshes', mip=2)
