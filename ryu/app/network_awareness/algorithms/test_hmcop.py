# coding=utf-8
"""

参数受限、参数最优：

没有指定QoS约束的话，返回最小跳路由
如果指定了QoS约束的话，就寻找满足约束条件下的 最短(跳数最小)的路由。

涉及带宽就 裁剪掉不符合条件的路径，然后调用最短路算法即可。
时延、抖动率、跳数都是加性的。

单纯的时延约束的话可以 用multipath-然后一一判断每条路，找到符合条件的路即可返回。

延迟带宽约束比较简单，通过裁剪掉带宽，就可以转变成上述单独的时延约束问题

时延约束的最小跳算法实现：


时延、带宽约束的最小跳算法实现：

这是什么傻逼玩意啊，这个头皮约时单独转带宽



"""

import matplotlib.pyplot as plt
import networkx as nx

from ryu.app.network_awareness.algorithms.dijkstraPathFinder import DijkstraPathFinder
from ryu.app.network_awareness.algorithms.lookAheadHmcpDijkstraRelaxation import LookAheadHmcpDijkstraRelaxation
from ryu.app.network_awareness.algorithms.reverseHmcpDijkstraRelaxation import ReverseHmcpDijkstraRelaxation


def print_topo(G):
    # 生成节点标签
    labels = {}
    labels[0] = '0'
    labels[1] = '1'
    labels[2] = '2'
    labels[3] = '3'
    labels[4] = '4'
    labels[5] = '5'

    check_constri = "jitter"

    # 获取graph中的边权重
    edge_labels = nx.get_edge_attributes(G, check_constri)
    print('weight of all edges:', edge_labels)

    # 生成节点位置
    pos = nx.circular_layout(G)
    print('position of all nodes:', pos)

    ncolor = ['b', 'b', 'y', 'b', 'r']

    # 把节点画出来
    nx.draw_networkx_nodes(G, pos, node_color=ncolor, node_size=500, alpha=0.8)

    # 把边画出来
    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5, edge_color='b')

    # 把节点的标签画出来
    nx.draw_networkx_labels(G, pos, labels, font_size=16)

    # 把边权重画出来
    nx.draw_networkx_edge_labels(G, pos, edge_labels)

    plt.title("network's topology of " + check_constri)

    plt.axis('on')
    # 去掉坐标刻度
    plt.xticks([])
    plt.yticks([])

    # plt.savefig(check_constri+".png")           #输出方式1: 将图像存为一个png格式的图片文件

    plt.show()


def init_topo():
    G = nx.Graph()
    G.add_nodes_from({0, 1, 2, 3, 4, 5})

    # Network topo
    G.add_edges_from([(0, 1), (0, 2), (1, 2), (1, 3), (1, 4), (2, 5), (3, 5),(4,5)])

    for l in G.adjacency():
        # print l[0]
        # print l[1]
        for j in l[1]:
            # print j
            G[l[0]][j]['weight'] = 1
            G[l[0]][j]['bw'] = 100
            G[l[0]][j]['delay'] = 10
            G[l[0]][j]['jitter'] = 10
            G[l[0]][j]['loss'] = 1

    # set delay
    G[0][1]['delay'] = 2
    G[0][2]['delay'] = 5
    G[1][2]['delay'] = 4
    G[1][3]['delay'] = 1
    G[1][4]['delay'] = 4
    G[2][5]['delay'] = 5
    G[3][5]['delay'] = 3
    G[4][5]['delay'] = 2

    # set jitter
    G[0][1]['jitter'] = 3
    G[0][2]['jitter'] = 6
    G[1][2]['jitter'] = 3
    G[1][3]['jitter'] = 2
    G[1][4]['jitter'] = 5
    G[2][5]['jitter'] = 4
    G[3][5]['jitter'] = 4
    G[4][5]['jitter'] = 1

    return G


def cheapest(open):
    return 1


def reverse_relax(graph, current, neighbor):
    return True


def buildPath(graph, start, end):
    pass


def reverse_dijkstra(graph, start, end):
    open = set()
    closed = set()
    open.add(start)
    while len(open) > 0:
        current = cheapest(open)
        neighbors = graph[open].keys()
        for neighbor in neighbors:
            if neighbor in closed:
                continue
            relaxed = reverse_relax(graph, current, neighbor)
            if relaxed:
                open.add(neighbor)
    return buildPath(graph, start, end)


def hmcp(graph, start, end, constraints):
    print "find a path wit src: %d and nend: %d" % (start, end)
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

        # print graph[0].keys()
        # for l in graph.adjacency():
        #     for ll in l:
        #         print ll
    return path


if __name__ == "__main__":
    # 初始化topo
    G = init_topo()

    # 打印topo
    print_topo(G)

    constraints = {"delay": 10, "jitter": 10}
    path = hmcp(G, 0, 5, constraints)
    print path
