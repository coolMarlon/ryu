from ryu.app.network_awareness.algorithms.Relaxation import Relaxation


class LookAheadHmcpDijkstraRelaxation(Relaxation):
    def __init__(self, constraints, reverse_relaxation):
        Relaxation.__init__(self)
        self.constraints = constraints
        self.reverse_relaxation = reverse_relaxation
        self.f = {}
        self.G = {}

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

        # The labels for the "tmp" node
        GTmp = []
        RTmp = []
        for m in range(len(self.constraints)):
            GTmp.append(0.0)
            RTmp.append(0.0)

        fTmp = float('-inf')

        # Pick the weight that increases the normalized cost the most
        for m in range(len(self.constraints)):
            newWeight = (self.G[node_from][m] + edge[self.constraints.keys()[m]]) / self.constraints.values()[m]
            if newWeight > fTmp:
                fTmp = newWeight

        # Fill the tmp aggregations
        for m in range(len(self.constraints)):
            GTmp[m] = self.G[node_from][m] + edge[self.constraints.keys()[m]]
            RTmp[m] = self.reverse_relaxation.getRDist(node_to, m)

        # Check and relax
        RTo = []
        for m in range(len(self.constraints)):
            RTo.append(self.reverse_relaxation.getRDist(node_to, m))

        if self.preferTheBest(node_from, node_to, GTmp, RTmp, self.G[node_to], RTo, fTmp, len(self.constraints)):
            self.f[node_to] = fTmp
            self.predecessors[node_to] = node_from
            for m in range(len(self.constraints)):
                self.G[node_to][m] = GTmp[m]
            return True
        return False

    def isCheaper(self, a, b):
        return self.f[a] < self.f[b]

    def constraintsFulfilled(self, node_to, numMetrics):
        for m in range(len(self.constraints)):
            if self.G[node_to][m] > self.constraints.values()[m]:
                return False
        return True

    def preferTheBest(self, node_a, node_b, Ga, Ra, Gb, Rb, fa, M):
        # Does A fulfill the constraints?
        aFulfills = True
        for m in range(len(self.constraints)):
            if Ga[m] + Ra[m] > self.constraints.values()[m]:
                aFulfills = False
                break
        if aFulfills:
            return True

        # Does B fulfill the constraints?
        bFulfills = True
        for m in range(len(self.constraints)):
            if Gb[m] + Rb[m] > self.constraints.values()[m]:
                bFulfills = False
                break
        if bFulfills:
            return False

        # If got here then just compare forward aggregates
        return fa < self.f[node_b]
