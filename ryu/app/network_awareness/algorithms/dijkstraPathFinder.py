class DijkstraPathFinder:
    def __init__(self, relaxation):
        self.relaxation = relaxation

    def find(self, graph, node_from, node_to):
        set_open = set()
        set_closed = set()
        set_open.add(node_from)

        # init relaxation
        self.relaxation.reset(graph, node_from)
        while len(set_open) > 0:
            # select the cheapest
            current = self.cheapest(set_open)
            set_open.remove(current)
            set_closed.add(current)
            neighbors = graph[current].keys()
            for neighbor in neighbors:
                if neighbor in set_closed:
                    continue
                # relax
                relaxed = self.relaxation.relax(graph, current, neighbor)
                if relaxed:
                    set_open.add(neighbor)
        return self.relaxation.buildPath(graph, node_from, node_to)

    def cheapest(self, set_node_open):
        candidate = None
        for node in set_node_open:
            if candidate is None or self.relaxation.isCheaper(node, candidate):
                candidate = node
        return candidate
