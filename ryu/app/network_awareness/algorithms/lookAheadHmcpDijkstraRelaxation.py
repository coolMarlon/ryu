class LookAheadHmcpDijkstraRelaxation:
    def __init__(self, constraints, reverse_relaxation):
        self.constraints = constraints
        self.reverse_relaxation = reverse_relaxation
        self.f = {}
        self.G = {}
        self.predecessors = {}

    def reset(self, graph, node_from):
        for node in graph.adjacency():
            metrics = []
            if node_from == node[0]:
                self.f[node[0]] = 0.0
                for m in range(len(self.constraints)):
                    metrics.append(0.0)
            else:
                self.f[node[0]] = float('inf')
                for m in range(len(self.constraints)):
                    metrics.append(float('inf'))
            self.G[node[0]] = metrics
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

    def isCheaper(self, a, b):
        return self.f[a] < self.f[b]

    def buildPath(self, graph, node_from, node_to):
        pass

    def constraintsFulfilled(self, node_to, numMetrics):
        return True
