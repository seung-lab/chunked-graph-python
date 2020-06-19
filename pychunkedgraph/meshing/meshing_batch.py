from taskqueue import TaskQueue, LocalTaskQueue, MockTaskQueue
import argparse
from pychunkedgraph.graph.chunkedgraph import ChunkedGraph # noqa
import numpy as np
from pychunkedgraph.meshing.meshing_sqs import MeshTask, MeshTaskSlow
from cloudvolume import CloudVolume, Storage

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--queue_name', type=str, default=None)
    parser.add_argument('--chunk_start', nargs=3, type=int)
    parser.add_argument('--chunk_end', nargs=3, type=int)
    parser.add_argument('--cg_name', type=str)
    parser.add_argument('--layer', type=int)
    parser.add_argument('--mip', type=int)
    parser.add_argument('--graphene_path', type=str)
    parser.add_argument('--mesh_dir', type=str)
    parser.add_argument('--max_shard_number', type=int, default=None)

    args = parser.parse_args()
    cv_mesh_dir = args.mesh_dir
    # cv_mesh_dir = 'graphene_meshes'

    cg = ChunkedGraph(graph_id=args.cg_name)

    chunks_arr = []
    for x in range(args.chunk_start[0],args.chunk_end[0]):
        for y in range(args.chunk_start[1], args.chunk_end[1]):
            for z in range(args.chunk_start[2], args.chunk_end[2]):
                chunks_arr.append((x, y, z))

    np.random.shuffle(chunks_arr)

    # cv = CloudVolume(args.graphene_path, mesh_dir=cv_mesh_dir)
    # stor = Storage(cg.meta.data_source.WATERSHED + '/' + cv_mesh_dir + '/initial/' + str(args.layer))
    # files_to_get = []
    # j = 0
    # for chunk in chunks_arr:
    #     chunk_id = cg.get_chunk_id(layer=args.layer, x=chunk[0], y=chunk[1], z=chunk[2])
    #     shard_filename = cv.mesh.readers[args.layer].get_filename(chunk_id)
    #     dash_index = shard_filename.index('-')
    #     for i in range(args.max_shard_number):
    #         files_to_get.append(shard_filename[0:dash_index+1] + str(i) + '.shard')
    #     if j % 10000 == 0 and j > 0:
    #         break
    #     j = j + 1
    # print("files")
    # # files_to_get = files_to_get[0:2000]
    # found_files = stor.files_exist(files_to_get)
    # # found_files = {}
    # # for cur_file in stor_result:
    # #     if cur_file["content"] is not None:
    # #         found_files[cur_file["filename"]] = True
    # import ipdb
    # ipdb.set_trace()


    class MeshTaskIterator(object):
        def __init__(self, chunks):
            self.chunks = chunks
        def __iter__(self):
            for chunk in self.chunks:
                chunk_id = cg.get_chunk_id(layer=args.layer, x=chunk[0], y=chunk[1], z=chunk[2])
                if args.max_shard_number is None:
                    yield MeshTask(args.cg_name, int(chunk_id), args.mip, args.graphene_path, cv_mesh_dir)
                else:
                    # shard_filename = cv.mesh.readers[args.layer].get_filename(chunk_id)
                    # dash_index = shard_filename.index('-')
                    for shard_no in range(args.max_shard_number):
                    #     check_file = shard_filename[0:dash_index+1] + str(shard_no) + '.shard'
                    #     if not found_files[check_file]:
                        yield MeshTaskSlow(args.cg_name, int(chunk_id), args.mip, args.graphene_path, cv_mesh_dir, shard_number=shard_no)

    if args.queue_name is not None:
        with TaskQueue(queue_name=args.queue_name) as tq:
            tq.insert_all(MeshTaskIterator(chunks_arr))
    else:
        tq = LocalTaskQueue(parallel=1)
        tq.insert_all(MeshTaskIterator(chunks_arr))