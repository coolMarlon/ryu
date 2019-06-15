# coding=utf-8
import unittest

from ryu.app.network_awareness.algorithms.humanTopology import HumanTopology

from ryu.app.network_awareness.algorithms.adaptive_routing_algorithm import adaptive_routing_algorithm


def get_graph():
    return HumanTopology.init_topology(
        path='/home/coolmarlon/Desktop/Code/mininet/examples/adaptive.mn')


class TestAdaptiveRouting(unittest.TestCase):

    def test_adaptive_routing_with_zero_constraint(self, graph=get_graph(), src=1, dst=6):
        constraints = {}
        path = adaptive_routing_algorithm(graph, src, dst, constraints)
        expected_path = [1, 3, 6]
        self.assertEqual(path, expected_path)

    def test_adaptive_routing_with_one_constraint(self, graph=get_graph(), src=1, dst=6):
        constraints = {"delay": 10}
        path = adaptive_routing_algorithm(graph, src, dst, constraints)
        expected_path = [1, 2, 4, 6]
        self.assertEqual(path, expected_path)

    def test_adaptive_routing_with_bw_constraint(self, graph=get_graph(), src=1, dst=6):
        constraints = {"bw": 12}
        path = adaptive_routing_algorithm(graph, src, dst, constraints)
        expected_path = [1, 2, 3, 6]
        self.assertEqual(path, expected_path)

    def test_adaptive_routing_with_bw_delay_constraint(self, graph=get_graph(), src=1, dst=6):
        constraints = {"bw": 11, "delay": 10}
        path = adaptive_routing_algorithm(graph, src, dst, constraints)
        expected_path = [1, 2, 3, 6]
        self.assertEqual(path, expected_path)

    def test_adaptive_routing_with_two_constraint(self, graph=get_graph(), src=1, dst=6):
        constraints = {"delay": 10, "jitter": 10}
        path = adaptive_routing_algorithm(graph, src, dst, constraints)
        expected_path = [1, 2, 5, 6]
        self.assertEqual(path, expected_path)

    def test_adaptive_routing_with_three_constraint(self, graph=get_graph(), src=1, dst=6):
        constraints = {"delay": 10, "jitter": 10, "bw": 10}
        path = adaptive_routing_algorithm(graph, src, dst, constraints)
        expected_path = [1, 3, 6]
        self.assertEqual(path, expected_path)


if __name__ == '__main__':
    unittest.main()
