"""
This file define the routing algorithms,
including Dijkstra, Floyd
Author:www.muzixing.com

Date                Work
2015/8/3            new
2015/8/3            done
2015/9/25           add best_paths_by_bw, using networkx
"""
import logging
import copy
import networkx as nx
from ryu import cfg
from ryu.openexchange.oxproto_common import OXP_MAX_CAPACITY, OXP_ADVANCED_BW

CONF = cfg.CONF
LOG = logging.getLogger('ryu.openexchange.routing_algorithm')


def floyd_dict(graph, src=None, topo=None):
    path = nx.all_pairs_dijkstra_path(graph)
    distance_graph = nx.all_pairs_dijkstra_path_length(graph)
    return distance_graph, path


def dijkstra(graph, src, topo=None):
    if graph is None:
        LOG.info("[Dijkstra]: Graph is empty.")
        return None
    path = nx.shortest_path(graph, source=src)
    distance_graph = nx.shortest_path_length(graph)
    return distance_graph, path


def get_intra_length(topo, pre, curr, next):
    if pre == curr or curr == next:
        return 0
    if (pre, curr) in topo.links:
        src_port = topo.links[(pre, curr)][1]
        if (curr, next) in topo.links:
            dst_port = topo.links[(curr, next)][0]
            if curr in topo.domains:
                if (src_port, dst_port) in topo.domains[curr].links:
                    in_dist = topo.domains[curr].links[(src_port, dst_port)]
                    return in_dist
                else:
                    LOG.debug("[%s]:%s->%s not found" % (
                        curr, src_port, dst_port))
                    return OXP_MAX_CAPACITY
    return 0


def full_floyd_dict(graph, src=None, topo=None):
    _graph = copy.deepcopy(graph)
    path = {}
    for src in _graph.nodes():
        path.setdefault(src, {src: [src]})
        for dst in _graph[src]:
            if src == dst:
                continue
            path[src].setdefault(dst, [src, dst])
            new_node = None
            for mid in _graph.nodes():
                if mid == dst:
                    continue

                _pre = src
                if mid in path[src]:
                    if len(path[src][mid]) > 1:
                        _pre = path[src][mid][-2]
                _next = dst
                if mid in path:
                    if dst in path[mid]:
                        if len(path[mid][dst]) > 1:
                            _next = path[mid][dst][1]

                in_dist = get_intra_length(topo, _pre, mid, _next)
                _len = _graph[src][mid]['weight'] + _graph[mid][dst]['weight']
                new_len = _len + in_dist
                if _graph[src][dst]['weight'] > new_len:
                    _graph[src][dst]['weight'] = new_len
                    new_node = mid
            if new_node:
                path[src][dst].insert(-1, new_node)
            elif _graph[src][dst]['weight'] == float('inf'):
                path[src][dst] = []
                LOG.debug("No path between %s and %s" % (src, dst))

    return _graph, path


def full_dijkstra(graph, src, topo):
    if graph is None:
        LOG.info("[Dijkstra]: Graph is empty.")
        return None
    # Initiation
    _graph = copy.deepcopy(graph)
    nodes = _graph.nodes()
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
        distance = float('inf')
        for v in visited:
            for d in nodes:
                _pre = src
                if len(path[src][v]) > 1:
                    _pre = path[src][v][-2]
                in_dist = get_intra_length(topo, _pre, v, d)
                new_dist = _graph[src][v]['weight'] + _graph[v][d]['weight']
                new_dist += in_dist

                if new_dist < distance:
                    distance = new_dist
                    next = d
                    pre = v
        if distance < float('inf'):
            path[src][next] = [i for i in path[src][pre]]
            path[src][next].append(next)
            distance_graph[next] = distance
            visited.append(next)
            nodes.remove(next)
        else:
            LOG.info("Next node is not found.")
            return None
    return distance_graph, path


def k_shortest_paths(graph, src, dst):
    path_generator = nx.shortest_simple_paths(graph, source=src,
                                              target=dst, weight='weight')
    return path_generator


def get_min_bw_of_inter_links(path, topo, min_bw):
    _len = len(path)
    if _len > 2:
        minimal_band_width = min_bw
        for i in xrange(_len-2):
            pre, curr, next = path[i], path[i+1], path[i+2]
            intra_bw = get_intra_length(topo, pre, curr, next)
            minimal_band_width = min(intra_bw, min_bw)
        return minimal_band_width
    return None


def get_min_bw_of_intra_links(graph, path, min_bw):
    _len = len(path)
    if _len > 1:
        minimal_band_width = min_bw
        for i in xrange(_len-1):
            pre, curr = path[i], path[i+1]
            if 'bandwidth' in graph[pre][curr]:
                bw = graph[pre][curr]['bandwidth']
                minimal_band_width = min(bw, min_bw)
            else:
                continue
        return minimal_band_width
    return None


def band_width_compare(graph, paths, best_paths, topo=None):
    capabilities = {}
    for src in paths:
        for dst in paths[src]:
            if src == dst:
                best_paths[src][src] = [src]
                capabilities.setdefault(src, {src: OXP_MAX_CAPACITY})
                capabilities[src][src] = OXP_MAX_CAPACITY
                continue
            max_bw_of_paths = 0
            best_path = paths[src][dst][0]
            for path in paths[src][dst]:
                min_bw = OXP_MAX_CAPACITY
                min_bw = get_min_bw_of_intra_links(graph, path, min_bw)
                if topo is not None and CONF.oxp_flags == OXP_ADVANCED_BW:
                    min_bw = get_min_bw_of_inter_links(path, topo, min_bw)
                if min_bw > max_bw_of_paths:
                    max_bw_of_paths = min_bw
                    best_path = path

            best_paths[src][dst] = best_path
            capabilities.setdefault(src, {dst: max_bw_of_paths})
            capabilities[src][dst] = max_bw_of_paths
    return capabilities, best_paths


def best_paths_by_bw(graph, src=None, topo=None):
    _graph = copy.deepcopy(graph)
    paths = {}
    best_paths = {}
    # find ksp in graph.
    for src in _graph.nodes():
        paths.setdefault(src, {src: [src]})
        best_paths.setdefault(src, {src: [src]})
        for dst in _graph.nodes():
            if src == dst:
                continue
            paths[src].setdefault(dst, [])
            best_paths[src].setdefault(dst, [])
            path_generator = k_shortest_paths(_graph, src, dst)

            k = CONF.oxp_k_paths
            for path in path_generator:
                if k <= 0:
                    break
                paths[src][dst].append(path)
                k -= 1
    # find best path by comparing bandwidth.
    capabilities, best_paths = band_width_compare(_graph, paths,
                                                  best_paths, topo)
    return capabilities, best_paths, paths


function = {'floyd': floyd_dict,
            'floyd_dict': floyd_dict,
            'full_floyd_dict': full_floyd_dict,
            'dijkstra': dijkstra,
            'full_dijkstra': full_dijkstra,
            'best_paths_by_bw': best_paths_by_bw}


def get_paths(graph, func, src=None, topo=None):
    """
    @graph: network toplogy graph in network_aware.
    @func function name
    @src: dpid.
    @topo: topo data
    """
    if func:
        result = function[func](graph, src=src, topo=topo)
        return result
    else:
        LOG.info("Function is None")
        return None
