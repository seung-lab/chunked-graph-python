from pychunkedgraph.graph.chunkedgraph import ChunkedGraph
cg = ChunkedGraph(graph_id='minnie3_v1')

from pychunkedgraph.graph.analysis import pathing

l2_path = pathing.find_l2_shortest_path(cg, 169464154984284186, 158831396440244866)
centroids = pathing.compute_rough_coordinate_path(cg, l2_path)