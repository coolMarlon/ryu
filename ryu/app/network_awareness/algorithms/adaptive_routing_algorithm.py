import networkx as nx

from ryu.app.network_awareness.algorithms.hmcp import hmcp


def adaptive_routing_algorithm(graph, src, dst, constraints):
    # type: (object, object, object, object) -> object
    # change the format of the src and dst switch to fit the networkx data structure.
    switch_src = "s" + str(src)
    switch_dst = "s" + str(dst)
    path = []
    constraints=constraints.
    # first pre treat the graph to remove links whcih don't follow the bandwidth requirement
    if "bw" in constraints:
        for l in graph.adjacency():
            for key, value in l[1].items():
                if value["bw"] < constraints['bw']:
                    graph.remove_edge(l[0], key)
        del constraints["bw"]
    # then execute the routing algorithm depends on the num of constraintss
    if len(constraints) == 0:
        switch_path = nx.shortest_path(graph, switch_src, switch_dst)
    elif len(constraints) == 1:
        switch_path = nx.shortest_path(graph, switch_src, switch_dst, weight=constraints.keys()[0])
    else:
        switch_path = hmcp(graph, switch_src, switch_dst, constraints)
    # last change the format of path to just num
    for node in switch_path:
        path.append(int(node[1:]))
    # return the path
    return path
