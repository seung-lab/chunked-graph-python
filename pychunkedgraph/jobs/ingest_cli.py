"""
cli for running ingest
"""
from collections import defaultdict, deque

import numpy as np
import click
from flask import current_app
from flask.cli import AppGroup

from .chunk_task import ChunkTask
from ..ingest.ran_ingestion_v2 import INGEST_CHANNEL
from ..ingest.ran_ingestion_v2 import ingest_into_chunkedgraph
from ..ingest.ran_ingestion_v2 import enqueue_parent_tasks
from ..ingest.ran_ingestion_v2 import enqueue_atomic_tasks

ingest_cli = AppGroup("ingest")

imanager = None
task_count = 0
tasks_cache_d = {}


def handle_job_result(*args, **kwargs):
    """handle worker return"""
    global tasks_cache_d, task_count
    task_id = args[0]["data"].decode("utf-8")
    task_count += 1

    with open(f"completed.txt", "a") as completed_f:
        completed_f.write(f"{task_id}\n")

    task = tasks_cache_d[task_id]
    parent_id = task.parent_id
    if parent_id:
        parent_task = tasks_cache_d[parent_id]
        parent_task.remove_child(task_id)

        if parent_task.dependencies == 0:
            enqueue_parent_tasks(
                imanager, parent_task.layer, parent_task.children_coords
            )


@ingest_cli.command("table")
# @click.argument("st_path", type=str)
# @click.argument("ws_path", type=str)
# @click.argument("cv_path", type=str)
# @click.argument("cg_table_id", type=str)
def run_ingest(cg_table_id=None):
    global imanager
    chunk_pubsub = current_app.redis.pubsub()
    chunk_pubsub.subscribe(**{INGEST_CHANNEL: handle_job_result})
    chunk_pubsub.run_in_thread(sleep_time=0.1)

    st_path = "gs://ranl/scratch/pinky100_ca_com/agg"
    ws_path = "gs://neuroglancer/pinky100_v0/ws/pinky100_ca_com"
    cv_path = "gs://akhilesh-pcg"
    cg_table_id = "akhilesh-pinky100-2"

    data_config = {
        "edge_dir": f"{cv_path}/akhilesh-pinky100-1/edges",
        "agglomeration_dir": f"{cv_path}/{cg_table_id}/agglomeration",
        "use_raw_edge_data": False,
        "use_raw_agglomeration_data": True,
    }

    imanager = ingest_into_chunkedgraph(
        storage_path=st_path,
        ws_cv_path=ws_path,
        cg_table_id=cg_table_id,
        layer=None,
        data_config=data_config,
    )
    root_task = _build_job_hierarchy()
    queue = deque([root_task.id])
    layer_counts = defaultdict(int)

    while queue:
        task_id = queue.pop()
        task = tasks_cache_d[task_id]
        layer_counts[task.layer] += len(task.children)
        queue.extendleft(task.children)
    print(layer_counts, sum(layer_counts.values()))
    enqueue_atomic_tasks(imanager)
    return tasks_cache_d


def init_ingest_cmds(app):
    app.cli.add_command(ingest_cli)


def _build_job_hierarchy():
    global tasks_cache_d
    root_task = ChunkTask(imanager.n_layers, np.array([0, 0, 0]))
    tasks_cache_d[root_task.id] = root_task

    start_layer = imanager.n_layers
    stop_layer = 2
    for layer in range(start_layer, stop_layer, -1):
        _build_layer(layer)
    return root_task


def _build_layer(layer):
    global tasks_cache_d
    layer_children_coords = imanager.chunk_coords // imanager.cg.fan_out ** (layer - 3)
    layer_children_coords = layer_children_coords.astype(np.int)
    layer_children_coords = np.unique(layer_children_coords, axis=0)

    layer_parents_coords = layer_children_coords // imanager.cg.fan_out
    layer_parents_coords = layer_parents_coords.astype(np.int)
    layer_parents_coords, indices = np.unique(
        layer_parents_coords, axis=0, return_inverse=True
    )
    parent_indices = np.arange(len(layer_parents_coords), dtype=np.int)
    for parent_idx in parent_indices:
        parent_coords = layer_parents_coords[parent_idx]
        parent_id = ChunkTask.get_id(layer, parent_coords)
        parent_task = tasks_cache_d[parent_id]
        children_coords = layer_children_coords[indices == parent_idx]
        parent_task.children_coords = children_coords
        for child_coords in children_coords:
            child = ChunkTask(layer - 1, child_coords, parent_id=parent_id)
            tasks_cache_d[child.id] = child
            parent_task.add_child(child.id)