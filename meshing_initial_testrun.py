from pychunkedgraph.backend.chunkedgraph import ChunkedGraph
from pychunkedgraph.meshing import meshgen
import cloudvolume


ws_cv_path = 'gs://seunglab2/drosophila_v0/ws_190410_FAFB_v02_ws_size_threshold_200'
ws_cv = cloudvolume.CloudVolume(ws_cv_path)
cg = ChunkedGraph('fly_v24')
new_info = ws_cv.info
new_info['mesh'] = 'mesh_testing/initial_testrun_meshes'
new_info['graph'] = cg.dataset_info['graph']
new_info['data_dir'] = ws_cv_path
mod_cg = ChunkedGraph('fly_v24', dataset_info=new_info)
for x in range(62,64):
    for y in range(68, 70):
        for z in range(8, 10):
            chunk_id = cg.get_chunk_id(None, 2, x, y, z)
            meshgen.chunk_mesh_task_new_remapping(cg, chunk_id, 'gs://seunglab2/drosophila_v0/ws_190410_FAFB_v02_ws_size_threshold_200', cv_mesh_dir='mesh_testing/initial_testrun_meshes', mip=1, max_err=320, dust_threshold=100)
