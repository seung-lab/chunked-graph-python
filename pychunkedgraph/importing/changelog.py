import dill
import numpy as np


def lookup_sv_ids(cg, coords):
    sv_ids = []

    for coord in coords:
        sv_ids.append(cg.cv[coord[0], coord[1], coord[2]])

    return np.array(sv_ids, dtyp=np.uint64)


def apply_merge(cg, cl_e):
    assert len(cl_e["sink_coords"]) == 1
    assert len(cl_e["source_coords"]) == 1

    sink_ids = lookup_sv_ids(cg, cl_e["sink_coords"])
    source_ids = lookup_sv_ids(cg, cl_e["source_coords"])

    ret = cg.add_edges(
        user_id=cl_e["user_id"],
        atomic_edges=np.array([sink_ids[0], source_ids[0]], dtype=np.uint64),
        source_coord=cl_e["sink_coords"],
        sink_coord=cl_e["source_coords"],

    )


def apply_split(cg, cl_e):
    sink_ids = lookup_sv_ids(cg, cl_e["sink_coords"])
    source_ids = lookup_sv_ids(cg, cl_e["source_coords"])

    ret = cg.remove_edges(
        user_id=cl_e["user_id"],
        source_ids=source_ids,
        sink_ids=sink_ids,
        source_coords=cl_e["sink_coords"],
        sink_coords=cl_e["source_coords"],
        mincut=True,
    )


def apply_change_log(cg, cl_path):

    with open(cl_path, "rb") as f:
        cl = dill.load(cl_path)

    for cl_k in cl.keys():
        print(cl_k)

        if cl[cl_k]["is_split"]:
            apply_split(cg, cl[cl_k])
        else:
            apply_merge(cg, cl[cl_k])