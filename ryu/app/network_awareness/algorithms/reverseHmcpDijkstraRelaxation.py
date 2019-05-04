from ryu.app.network_awareness.algorithms.Relaxation import Relaxation


class ReverseHmcpDijkstraRelaxation(Relaxation):
    def __init__(self, constraints):
        # super(ReverseHmcpDijkstraRelaxation, self).__init__()
        Relaxation.__init__(self)
        self.constraints = constraints
        self.r = {}
        self.R = {}

    def reset(self, graph, node_from):
        for node in graph.adjacency():
            metrics = []
            if node_from == node[0]:
                self.r[node[0]] = 0.0
                for m in range(len(self.constraints)):
                    metrics.append(0.0)
            else:
                self.r[node[0]] = float('inf')
                for m in range(len(self.constraints)):
                    metrics.append(float('inf'))
            self.R[node[0]] = metrics
            self.predecessors[node[0]] = node

    def relax(self, graph, node_from, node_to):
        edge = graph[node_from][node_to]
        maxWeight = float('-inf')
        for m in range(len(self.constraints)):
            newWeight = (self.R[node_from][m] + edge[self.constraints.keys()[m]]) \
                        / self.constraints.values()[m]
            if newWeight > maxWeight:
                maxWeight = newWeight
        if self.r[node_to] > maxWeight:
            self.r[node_to] = maxWeight
            self.predecessors[node_to] = node_from
            for m in range(len(self.constraints)):
                self.R[node_to][m] = self.R[node_from][m] + edge[self.constraints.keys()[m]]
            return True
        return False

    def isCheaper(self, node_a, node_b):
        return self.r[node_a] < self.r[node_b]

    def guaranteedFailure(self, node_from, numMetrics):
        return self.r[node_from] > numMetrics

    def getRDist(self, node, metric):
        return self.R[node][metric]