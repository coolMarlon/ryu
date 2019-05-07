class Relaxation:
    def __init__(self):
        self.predecessors = {}

    def buildPath(self, graph, node_from, node_to):
        nodes = []
        current = node_to
        while current != node_from:
            if self.predecessors[current] == current and current != node_from:
                return None
            nodes.append(current)
            current = self.predecessors[current]
        nodes.append(node_from)
        nodes.reverse()
        return nodes
