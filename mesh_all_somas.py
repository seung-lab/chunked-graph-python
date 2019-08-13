from pychunkedgraph.meshing.meshgen import remeshing, mesh_segid_thread
from pychunkedgraph.backend.chunkedgraph import ChunkedGraph
import pychunkedgraph
import cloudvolume
import numpy as np
import os
import multiwrapper.multiprocessing_utils as mu
from analysisdatalink.datalink_ext import AnalysisDataLinkExt as AnalysisDataLink

dataset_name = 'pinky100'
mat_version = 175
HOME = os.path.expanduser("~")
orig_cv_path = 'https://storage.googleapis.com/neuroglancer/nkem/pinky100_v0/ws/lost_no-random/bbox1_0'
cv_path = f'file://{HOME}/friday_harbor/friday_harbor_pinky100_sv16/'
cv_mesh_dir = "friday_harbor_meshes"
cg = ChunkedGraph("pinky100_sv16")
stop_layer=2
mip = 2
n_threads = 1
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

cg_info = cg.get_serialized_info()
margs = []
for seg_id in seg_ids:
    margs.append((cg_info, cv_path, cv_mesh_dir, seg_id, stop_layer, mip))

mu.multisubprocess_func(pychunkedgraph.meshing.meshgen.mesh_segid_thread, margs, n_threads=n_threads)

# lvl2_ids = cg.get_subgraph_nodes(seg_id, return_layers=[2])
# remeshing(cg, lvl2_ids, stop_layer=9, cv_path=cv_path, cv_mesh_dir='meshes', mip=2)
