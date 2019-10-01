import itertools
import numpy as np
import pickle


from ..utils.redis import get_redis_connection
from ..utils.redis import get_rq_queue
from ..backend.chunkedgraph_utils import compute_bitmasks
from ..backend.chunkedgraph import ChunkedGraph
from ..backend.definitions.config import DataSource
from ..backend.definitions.config import GraphConfig
from ..backend.definitions.config import BigTableConfig

# TODO
# group parameters
# refactor their usage in all modules
# get rid of `ingest_into_chunkedgraph`
# use IngestionManager directly


class IngestionManager(object):
    def __init__(
        self,
        data_source: DataSource,
        graph_config: GraphConfig,
        bigtable_config: BigTableConfig,
        cv=None,
        task_q_name="test",
        build_graph=True,
    ):

        # n_layers
        self._data_source = data_source
        self._graph_config = graph_config
        self._bigtable_config = bigtable_config

        self._cg = None

        self._cv = cv
        self._chunk_coords = None
        self._layer_bounds_d = None
        self._redis_connection = None
        self._task_q_name = task_q_name
        self._task_q = None
        self._build_graph = build_graph
        self._bitmasks = None
        self._bounds = None
        self._redis = None

    @property
    def data_source(self):
        return self._data_source

    @property
    def edge_dtype(self):
        if self._data_source.data_version == 4:
            dtype = [
                ("sv1", np.uint64),
                ("sv2", np.uint64),
                ("aff_x", np.float32),
                ("area_x", np.uint64),
                ("aff_y", np.float32),
                ("area_y", np.uint64),
                ("aff_z", np.float32),
                ("area_z", np.uint64),
            ]
        elif self._data_source.data_version == 3:
            dtype = [
                ("sv1", np.uint64),
                ("sv2", np.uint64),
                ("aff_x", np.float64),
                ("area_x", np.uint64),
                ("aff_y", np.float64),
                ("area_y", np.uint64),
                ("aff_z", np.float64),
                ("area_z", np.uint64),
            ]
        elif self._data_source.data_version == 2:
            dtype = [
                ("sv1", np.uint64),
                ("sv2", np.uint64),
                ("aff", np.float32),
                ("area", np.uint64),
            ]
        else:
            raise Exception()

        return dtype

    @property
    def cg(self):
        if self._cg is None:
            self._cg = ChunkedGraph(table_id=self._graph_config.graph_id, **kwargs)
        return self._cg

    @property
    def bounds(self):
        if self._bounds:
            return self._bounds
        cv_bounds = np.array(self._cv.bounds.to_list()).reshape(2, -1).T
        self._bounds = cv_bounds.copy()
        self._bounds -= cv_bounds[:, 0:1]
        return self._bounds

    @property
    def chunk_id_bounds(self):
        return np.ceil((self.bounds / self._chunk_size[:, None])).astype(np.int)

    @property
    def layer_chunk_bounds(self):
        if self._layer_bounds_d:
            return self._layer_bounds_d
        layer_bounds_d = {}
        for layer in range(2, self.n_layers):
            layer_bounds = self.chunk_id_bounds / (2 ** (layer - 2))
            layer_bounds_d[layer] = np.ceil(layer_bounds).astype(np.int)
        self._layer_bounds_d = layer_bounds_d
        return self._layer_bounds_d

    @property
    def chunk_coord_gen(self):
        return itertools.product(*[range(*r) for r in self.chunk_id_bounds])

    @property
    def chunk_coords(self):
        if not self._chunk_coords is None:
            return self._chunk_coords
        self._chunk_coords = np.array(list(self.chunk_coord_gen), dtype=np.int)
        return self._chunk_coords

    @property
    def n_layers(self):
        if self._n_layers is None:
            self._n_layers = self.cg.n_layers
        return self._n_layers

    @property
    def task_q(self):
        if self._task_q:
            return self._task_q
        self._task_q = get_rq_queue(self._task_q_name)
        return self._task_q

    @property
    def redis(self):
        if self._redis:
            return self._redis
        self._redis = get_redis_connection()
        return self._redis

    @property
    def build_graph(self):
        return self._build_graph

    def get_serialized_info(self, pickled=False):
        info = {
            "data_source": self._data_source,
            "graph_config": self._graph_config,
            "bigtable_config": self._bigtable_config,
        }
        if pickled:
            return pickle.dumps(info)
        return info

    def is_out_of_bounds(self, chunk_coordinate):
        if not self._bitmasks:
            self._bitmasks = compute_bitmasks(
                self.n_layers, 2, s_bits_atomic_layer=self._s_bits_atomic_layer
            )
        return np.any(chunk_coordinate < 0) or np.any(
            chunk_coordinate > 2 ** self._bitmasks[1]
        )

    @classmethod
    def from_pickle(cls, serialized_info):
        return cls(**pickle.loads(serialized_info))

