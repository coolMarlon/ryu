# coding=utf-8
import json

import matplotlib.pyplot as plt
import networkx as nx


class HumanTopology:
    def __init__(self):
        pass

    @staticmethod
    def print_topology(graph, check_constraint=None, save_figure=False):
        if check_constraint is None:
            nx.draw(graph, with_labels=True)
            plt.show()
            return
        # 生成节点标签
        labels = {}
        for l in graph.adjacency():
            labels[l[0]] = l[0]

            # 获取graph中的边权重
        edge_labels = nx.get_edge_attributes(graph, check_constraint)
        print('weight of all edges:', edge_labels)

        # 生成节点位置
        pos = nx.circular_layout(graph)
        print('position of all nodes:', pos)

        node_color = []
        for i in range(0, len(graph)):
            node_color.append('b')
        # if len(graph) >= 2:
        #     node_color.append('r')

        # 把节点画出来
        nx.draw_networkx_nodes(graph, pos, node_color=node_color, node_size=500, alpha=0.8)

        # 把边画出来
        nx.draw_networkx_edges(graph, pos, width=1.0, alpha=0.5, edge_color='black')

        # 把节点的标签画出来
        nx.draw_networkx_labels(graph, pos, labels, font_size=16)

        # 把边权重画出来
        nx.draw_networkx_edge_labels(graph, pos, edge_labels)

        plt.title("network's topology of " + check_constraint)

        plt.axis('on')
        # 去掉坐标刻度
        plt.xticks([])
        plt.yticks([])

        if save_figure:
            plt.savefig(check_constraint + ".png")  # 输出方式1: 将图像存为一个png格式的图片文件

        plt.show()

    @staticmethod
    def init_topology(path=None):
        # 从mn文件即json文件构造图
        if path is not None:
            try:
                f = open(path, 'r')  # 打开文件
                json_string = f.read()  # 读取文件内容
                parsed_json = json.loads(json_string)
                graph = nx.Graph()
                for switch in parsed_json['switches']:
                    graph.add_node(switch['opts']['hostname'].encode("utf8"))

                for link in parsed_json['links']:
                    if link['src'].encode("utf8").startswith('h') \
                            or link['dest'].encode("utf8").startswith('h'):
                        continue
                    graph.add_edge(link['src'].encode("utf8"), link['dest'].encode("utf8"))
                    for key, value in link['opts'].items():
                        if key.encode("utf8") == 'bw':
                            int_value = value
                        else:
                            int_value = int(value.encode("utf8"))
                        graph[link['src'].encode("utf8")][link['dest'].encode("utf8")] \
                            [key.encode("utf8")] = int_value
            finally:
                if f:
                    f.close()  # 确保文件被关闭
                    return graph
        return graph
