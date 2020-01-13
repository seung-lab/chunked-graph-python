import dill
import numpy as np


def apply_changelog(cg, cl_path):
    cl = load_change_log(cl_path)
    cl_keys = np.array(list(cl.keys()))
    cl_time_stamps = []

    for cl_key in cl_keys:
        cl_entry = cl[cl_key]
        cl_time_stamps.append(cl_entry["timestamp"])

    cl_time_stamp_sorting = np.argsort(cl_time_stamps)

    for cl_key in cl_keys[cl_time_stamp_sorting]:
        cl_entry = cl[cl_key]
        apply_change(cg, cl_entry)


def load_change_log(cl_path):
    f = open(cl_path, "rb")
    cl = dill.load(f)
    f.close()

    return cl


def apply_change(cg, cl_entry):
    if cl_entry["is_split"]:
        apply_split(cg, cl_entry)
    else:
        apply_merge(cg, cl_entry)


def apply_split(cg, cl_entry):
    print("split")


def apply_merge(cg, cl_entry):
    print("merge")

