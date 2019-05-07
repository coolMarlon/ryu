# coding=utf-8
import unittest

from ryu.app.network_awareness.algorithms.hmcp import hmcp
from ryu.app.network_awareness.algorithms.humanTopology import HumanTopology


class TestHMCP(unittest.TestCase):
    def test_hmcp(self):
        # init topology
        graph = HumanTopology.init_topology()

        constraints = {"delay": 10, "jitter": 10}
        path = hmcp(graph, 0, 5, constraints)
        expected_path = [0, 1, 4, 5]
        self.assertEqual(path, expected_path)

    def test_hmcp_with_graph(self):
        graph = HumanTopology.init_topology(
            path='/home/coolmarlon/Desktop/Code/mininet/examples/adaptive.mn')
        constraints = {"delay": 10, "jitter": 10}
        for l in graph.adjacency():
            print l
        path = hmcp(graph, 's1', 's6', constraints)
        print path
        expected_path = ['s1', 's2', 's5', 's6']
        self.assertEqual(path, expected_path)


if __name__ == '__main__':
    unittest.main()
