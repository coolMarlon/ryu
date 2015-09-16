"""
This file define the routing algorithms,
including Dijkstra, Floyd, Prim and Kruskal.
Author:www.muzixing.com

Date                Work
2015/8/3            new
2015/8/3            done
"""
import logging
from ryu.openexchange.oxproto_common import OXP_MAX_LEN

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
            elif graph[src][dst] == float('inf'):
                path[src][dst] = []
                LOG.debug("No path between %s and %s" % (src, dst))
    return graph, path


def floyd_dict(graph, src=None, topo=None):
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
            elif graph[src][dst] == float('inf'):
                path[src][dst] = []
                LOG.debug("No path between %s and %s" % (src, dst))
    return graph, path


def full_floyd_dict(graph, src=None, topo=None):
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

                new_len = graph[src][mid] + graph[mid][dst] + in_dist
                in_dist = 0
                src_port = dst_port = None

                if graph[src][dst] > new_len:
                    graph[src][dst] = new_len
                    new_node = mid
            if new_node:
                path[src][dst].insert(-1, new_node)
            elif graph[src][dst] == float('inf'):
                path[src][dst] = []
                LOG.debug("No path between %s and %s" % (src, dst))
    return graph, path


def dijkstra(graph, src, topo=None):
    if graph is None:
        LOG.info("[Dijkstra]: Graph is empty.")
        return None
    # Initiation
    nodes = graph.keys()
    visited = [src]
    path = {src: {src: [src]}}
    if src not in nodes:
        LOG.debug("[Dijkstra]:Src[%s] is not in nodes." % src)
        return None
    else:
        nodes.remove(src)

    distance_graph = {src: 0}
    pre = next = src

    while nodes:
        distance = OXP_MAX_LEN
        for v in visited:
            for d in nodes:
                new_dist = graph[src][v] + graph[v][d]
                if new_dist <= distance:
                    distance = new_dist
                    next = d
                    pre = v
                if new_dist < graph[src][d]:
                    graph[src][d] = new_dist

        if distance < OXP_MAX_LEN:
            path[src][next] = [i for i in path[src][pre]]
            path[src][next].append(next)
            distance_graph[next] = distance
            visited.append(next)
            nodes.remove(next)
        else:
            LOG.debug("Next node is not found.")
            return None
    return distance_graph, path


def get_intra_length(topo, pre, mid, next):
    if (pre, mid) in topo.links:
        src_port = topo.links[(pre, mid)][1]
        if (mid, next) in topo.links:
            dst_port = topo.links[(mid, next)][0]
            if (src_port, dst_port) in topo.domains[mid].links:
                in_dist = topo.domains[mid].links[(src_port, dst_port)]
                return in_dist
    return 0


def full_dijkstra(graph, src, topo):
    if graph is None:
        LOG.info("[Dijkstra]: Graph is empty.")
        return None
    # Initiation
    nodes = graph.keys()
    visited = [src]
    path = {src: {src: [src]}}
    if src not in nodes:
        LOG.info("[Dijkstra]:Src[%s] is not in nodes." % src)
        return None
    else:
        nodes.remove(src)
    distance_graph = {src: 0}
    pre = next = src

    while nodes:
        distance = OXP_MAX_LEN
        for v in visited:
            for d in nodes:
                if len(path[src][v]) > 1:
                    _pre = path[src][v][-2]
                else:
                    _pre = src
                in_dist = get_intra_length(topo, _pre, v, d)
                new_dist = graph[src][v] + graph[v][d] + in_dist

                if new_dist < distance:        # record the min edge.
                    distance = new_dist
                    next = d
                    pre = v
        if distance < OXP_MAX_LEN:
            path[src][next] = [i for i in path[src][pre]]
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
