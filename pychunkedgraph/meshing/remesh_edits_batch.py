from taskqueue import TaskQueue, LocalTaskQueue, MockTaskQueue
import argparse
import numpy as np
from pychunkedgraph.meshing.meshing_sqs import RemeshEditsTask

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--queue_name', type=str, default=None)
    parser.add_argument('--cg_name', type=str)
    parser.add_argument('--root_id', type=int, default=None)
    parser.add_argument('--root_ids_file', type=str, default=None)
    parser.add_argument('--skip_cache', action='store_true')
    parser.add_argument('--write_finished', type=str, default=None)

    args = parser.parse_args()
    cache = not args.skip_cache

    if args.root_ids_file:
        root_ids = np.load(args.root_ids_file)
    elif args.root_id:
        root_ids = [args.root_id]
    else:
        raise ValueError('Must specify root_id or root_ids_file')

    class MeshTaskIterator(object):
        def __init__(self, roots):
            self.roots = roots
        def __iter__(self):
            for root_id in self.roots:
                yield RemeshEditsTask(args.cg_name, int(root_id), cache, args.write_finished)

    if args.queue_name is not None:
        with TaskQueue(queue_name=args.queue_name) as tq:
            tq.insert_all(MeshTaskIterator(root_ids))
    else:
        tq = LocalTaskQueue(parallel=1)
        tq.insert_all(MeshTaskIterator(root_ids))