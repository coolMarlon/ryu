import unittest

from ryu.app.network_awareness.algorithms.humanTopology import HumanTopology


class TestTopology(unittest.TestCase):
    def test_init(self):
        graph = HumanTopology.init_topology()
        self.assertEqual(len(graph), 6)
        pass

    def test_init_with_file(self):
        graph = HumanTopology.init_topology(
            path='/home/coolmarlon/Desktop/Code/mininet/examples/multipath_diff_delay.mn')
        print graph

    def test_print(self):
        graph = HumanTopology.init_topology()
        HumanTopology.print_topology(graph, check_constraint="delay")
        self.assertEqual(1, 1)

    def test_print_with_file(self):
        graph = HumanTopology.init_topology(
            path='/home/coolmarlon/Desktop/Code/mininet/examples/adaptive.mn')
        HumanTopology.print_topology(graph, check_constraint="delay")


if __name__ == '__main__':
    unittest.main()
