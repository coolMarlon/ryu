"""
This file define the routing algorithms,
including Dijkstra, Floyd, Prim and Kruskal.
Author:www.muzixing.com

Date                Work
2015/8/3            new
2015/8/3            done
"""
import logging

LOG = logging.getLogger('ryu.openexchange.routing_algorithm')


def floyd(graph, src=None, topo=None):
    length = len(graph)
    path = {}

    for i in xrange(length):
        path.setdefault(i, {})
        for j in xrange(length):
            if i == j:
                continue
            path[i].setdefault(j, [i, j])
            new_node = None

            for k in xrange(length):
                if k == j:
                    continue
                new_len = graph[i][k] + graph[k][j]
                if graph[i][j] > new_len:
                    graph[i][j] = new_len
                    new_node = k
            if new_node:
                path[i][j].insert(-1, new_node)
    return graph, path


def floyd_dict(graph, src=None, topo=None):
    length = len(graph)
    path = {}

    for src in graph:
        path.setdefault(src, {src: [src]})
        for dst in graph[src]:
            if src == dst:
                continue
            path[src].setdefault(dst, [src, dst])
            new_node = None

            for mid in graph:
                if mid == dst:
                    continue
                new_len = graph[src][mid] + graph[mid][dst]
                if graph[src][dst] > new_len:
                    graph[src][dst] = new_len
                    new_node = mid
            if new_node:
                path[src][dst].insert(-1, new_node)
    return graph, path


def full_floyd_dict(graph, src=None, topo=None):
    length = len(graph)
    path = {}
    src_port = dst_port = None
    in_dist = 0
    domains = topo.domains
    links = topo.links

    for src in graph:
        path.setdefault(src, {src: [src]})
        for dst in graph[src]:
            if src == dst:
                continue
            path[src].setdefault(dst, [src, dst])
            new_node = None

            for mid in graph:
                if mid == dst:
                    continue

                if (src, mid) in links:
                    src_port = links[(src, mid)][1]
                    if (mid, dst) in links:
                        dst_port = links[(mid, dst)][0]
                if src_port is not None and dst_port is not None:
                    if (src_port, dst_port) in domains[mid].links:
                        in_dist = domains[mid].links[(src_port, dst_port)]
                    else:
                        pass

                new_len = graph[src][mid] + graph[mid][dst] + in_dist
                in_dist = 0
                src_port = dst_port = None
                if graph[src][dst] > new_len:
                    graph[src][dst] = new_len
                    new_node = mid
            if new_node:
                path[src][dst].insert(-1, new_node)
    return graph, path


def dijkstra(graph, src, topo=None):
    if graph is None:
        LOG.info("[Dijkstra]: Graph is empty.")
        return None
    # Initiation
    length = len(graph)
    if isinstance(graph, list):
        nodes = [i for i in xrange(length)]
    elif isinstance(graph, dict):
        nodes = graph.keys()

    visited = [src]
    path = {src: {src: []}}
    if src not in nodes:
        LOG.debug("[Dijkstra]:Src[%s] is not in nodes." % src)
        return None
    else:
        nodes.remove(src)

    distance_graph = {src: 0}
    pre = next = src
    no_link_value = 100000

    # Entire graph include non-links.
    while nodes:
        distance = no_link_value
        for v in visited:
            for d in nodes:
                new_dist = graph[src][v] + graph[v][d]
                if new_dist <= distance:
                    distance = new_dist
                    next = d
                    pre = v
                    graph[src][d] = new_dist

        if distance < no_link_value:
            path[src][next] = [i for i in path[src][pre]]
            path[src][next].append(next)
            distance_graph[next] = distance
            visited.append(next)
            nodes.remove(next)
        else:
            LOG.debug("Next node is not found.")
            return None
    return distance_graph, path


def full_dijkstra(graph, src, topo):
    if graph is None:
        LOG.info("[Dijkstra]: Graph is empty.")
        return None
    # Initiation
    length = len(graph)
    if isinstance(graph, list):
        nodes = [i for i in xrange(length)]
    elif isinstance(graph, dict):
        nodes = graph.keys()

    visited = [src]
    path = {src: {src: []}}
    if src not in nodes:
        LOG.info("[Dijkstra]:Src[%s] is not in nodes." % src)
        return None
    else:
        nodes.remove(src)

    distance_graph = {src: 0}
    pre = next = src
    src_port = dst_port = None
    no_link_value = 100000
    in_dist = 0
    domains = topo.domains
    links = topo.links

    # Entire graph include non-links.
    while nodes:
        distance = no_link_value
        for v in visited:
            for d in nodes:
                if (pre, v) in links:
                    src_port = links[(pre, v)][1]
                    if (v, d) in links:
                        dst_port = links[(v, d)][0]
                if src_port is not None and dst_port is not None:
                    if (src_port, dst_port) in domains[v].links:
                        in_dist = domains[v].links[(src_port, dst_port)]
                    else:
                        pass

                new_dist = graph[src][v] + graph[v][d]  # + in_dist
                in_dist = 0
                src_port = dst_port = None
                if new_dist <= distance:
                    distance = new_dist
                    next = d
                    pre = v
                    graph[src][d] = new_dist

        if distance < no_link_value:
            path[src][next] = [i for i in path[src][pre]]
            print "next, dist: ", next, distance
            path[src][next].append(next)
            distance_graph[next] = distance
            visited.append(next)
            nodes.remove(next)
        else:
            LOG.info("Next node is not found.")
            return None
    return distance_graph, path


function = {'floyd': floyd,
            'floyd_dict': floyd_dict,
            'full_floyd_dict': full_floyd_dict,
            'dijkstra': dijkstra,
            'full_dijkstra': full_dijkstra}


def get_paths(graph, func, src=None, topo=None):
    """
    @graph: network toplogy graph in network_aware.
    @func function name
    @src: dpid.
    @topo: topo data
    """
    distance_graph, path_dict = function[func](graph, src=src, topo=topo)
    return distance_graph, path_dict
