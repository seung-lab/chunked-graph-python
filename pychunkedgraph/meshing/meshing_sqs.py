from taskqueue import RegisteredTask
from pychunkedgraph.meshing import meshgen
import numpy as np
import datetime

class MeshTask(RegisteredTask):
    def __init__(self, cg_name, layer, chunk_id, mip, cache=True, time_stamp=None):
        super().__init__(cg_name, layer, chunk_id, mip, cache, time_stamp)

    def execute(self):
        cg_name = self.cg_name
        chunk_id = np.uint64(self.chunk_id)
        mip = self.mip
        layer = self.layer
        time_stamp = None
        if self.time_stamp:
            time_stamp = datetime.datetime.utcfromtimestamp(self.time_stamp)
        if layer == 2:
            result = meshgen.chunk_initial_mesh_task(
                cg_name,
                chunk_id,
                None,
                mip=mip,
                sharded=True,
                cache=self.cache,
                time_stamp=time_stamp
            )
        else:
            result = meshgen.chunk_initial_sharded_stitching_task(
                cg_name, chunk_id, mip, cache=self.cache, time_stamp=time_stamp
            )
        print(result)


class RemeshEditsTask(RegisteredTask):
    def __init__(self, cg_name, root_id, cache=True, write_finished=None):
        super().__init__(cg_name, root_id, cache, write_finished)
    
    def execute(self):
        cg_name = self.cg_name
        root_id = np.uint64(self.root_id)
        meshgen.remesh_edits_to_root(cg_name, root_id, self.cache, self.write_finished)
