from taskqueue import RegisteredTask
from pychunkedgraph.meshing import meshgen
from pychunkedgraph.backend.chunkedgraph import ChunkedGraph
import numpy as np


class MeshTask(RegisteredTask):
    def __init__(self, cg_name, chunk_id, mip, mesh_path=None, dust_threshold=0):
        super().__init__(cg_name, chunk_id, mip, mesh_path, dust_threshold)

    def execute(self):
        cg = ChunkedGraph(self.cg_name)
        chunk_id = np.uint64(self.chunk_id)
        mip = self.mip
        result = meshgen.chunk_mesh_task_new_remapping(
            None,
            chunk_id,
            mip=mip,
            cg=cg,
            mesh_path=self.mesh_path,
            dust_threshold=self.dust_threshold
        )
