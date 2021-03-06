import sys
from multiprocessing import cpu_count

import numpy as np

from pychunkedgraph.ingest import IngestConfig
from pychunkedgraph.ingest.manager import IngestionManager
from pychunkedgraph.ingest.main import start_ingest
from pychunkedgraph.ingest.utils import initialize_chunkedgraph
from pychunkedgraph.backend import DataSource
from pychunkedgraph.backend import GraphConfig
from pychunkedgraph.backend import BigTableConfig
from pychunkedgraph.backend import ChunkedGraphMeta


if __name__ == "__main__":
    name = sys.argv[1]
    count = int(sys.argv[2])
    bigtable_config = BigTableConfig(table_id_prefix=name)

    graph_config = GraphConfig(
        graph_id=f"{bigtable_config.table_id_prefix}",
        chunk_size=np.array([256, 256, 512], dtype=int),
        overwrite=True,
    )

    data_source = DataSource(
        agglomeration="gs://ranl-scratch/190410_FAFB_v02_ws_size_threshold_200/agg",
        watershed="gs://microns-seunglab/drosophila_v0/ws_190410_FAFB_v02_ws_size_threshold_200",
        edges="gs://chunked-graph/190410_FAFB_v02/edges",
        components="gs://chunked-graph/190410_FAFB_v02/components",
        use_raw_edges=False,
        use_raw_components=False,
        data_version=2,
    )

    meta = ChunkedGraphMeta(data_source, graph_config, bigtable_config)
    initialize_chunkedgraph(meta)