# coding=utf-8
from ryu.app.network_awareness.algorithms.dijkstraPathFinder import DijkstraPathFinder
from ryu.app.network_awareness.algorithms.lookAheadHmcpDijkstraRelaxation import LookAheadHmcpDijkstraRelaxation
from ryu.app.network_awareness.algorithms.reverseHmcpDijkstraRelaxation import ReverseHmcpDijkstraRelaxation


def hmcp(graph, start, end, constraints):
    # print "find a path wit src: %d and nend: %d" % (start, end)
    print "constraints:", constraints

    # Search reverse.
    reverse_relaxation = ReverseHmcpDijkstraRelaxation(constraints)
    reverse_path_finder = DijkstraPathFinder(reverse_relaxation)
    if reverse_path_finder.find(graph, end, start) is None:
        return None

    if reverse_relaxation.guaranteedFailure(end, len(constraints)):
        return None

    # Search look ahead
    look_ahead_relaxation = LookAheadHmcpDijkstraRelaxation(constraints, reverse_relaxation)
    look_ahead_path_finder = DijkstraPathFinder(look_ahead_relaxation)
    path = look_ahead_path_finder.find(graph, start, end)
    if path is None:
        return None
    if look_ahead_relaxation.constraintsFulfilled(end, len(constraints)) is False:
        return None

    return path

