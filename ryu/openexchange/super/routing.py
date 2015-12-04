# conding=utf-8
import logging
import struct
import networkx as nx

from operator import attrgetter
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp

from ryu.openexchange.network import network_aware
from ryu.openexchange.network import network_monitor
from ryu.openexchange.domain import setting
from ryu.openexchange.routing_algorithm.routing_algorithm import get_paths
from ryu.openexchange.utils import utils
from ryu.openexchange.utils.utils import check_model_is_hop, check_model_is_bw
from ryu.openexchange.event import oxp_event


class Routing(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(Routing, self).__init__(*args, **kwargs)
        self.module_topo = None
        self.topology = None
        self.location = None
        self.domains = {}
        self.graph = nx.DiGraph()
        self.paths = {}
        self.capabilities = {}

    @set_ev_cls(oxp_event.EventOXPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        domain = ev.domain
        if ev.state == MAIN_DISPATCHER:
            if domain.id not in self.domains.keys():
                self.domains.setdefault(domain.id, None)
                self.domains[domain.id] = domain
            if self.module_topo is None:
                self.module_topo = lookup_service_brick('oxp_topology')
                self.topology = self.module_topo.topo
                self.location = self.module_topo.location
        if ev.state == DEAD_DISPATCHER:
            del self.domains[domain.id]

    def get_host_location(self, host_ip):
        for domain_id in self.location.locations:
            if host_ip in self.location.locations[domain_id]:
                return domain_id
        self.logger.debug("%s location is not found." % host_ip)
        return None

    def get_graph(self, link_list, nodes):
        graph = nx.DiGraph()
        if check_model_is_hop():
            for src in nodes.keys():
                for dst in nodes.keys():
                    graph.add_edge(src, dst, weight=float('inf'))
                    if src == dst:
                        graph[src][src]['weight'] = 0
                    elif (src, dst) in link_list:
                        graph[src][dst]['weight'] = link_list[(src, dst)][2]
        if check_model_is_bw():
            for src in nodes.keys():
                for dst in nodes.keys():
                    graph.add_edge(src, dst, weight=float('inf'))
                    if src == dst:
                        graph[src][src]['weight'] = 0
                    elif (src, dst) in link_list:
                        graph[src][dst]['weight'] = 1
                        graph[src][dst]['bandwidth'] = link_list[(src, dst)][2]

        return graph

    def get_bw_graph(self, graph, link_list):
        for src in graph.nodes():
            for dst in graph[src]:
                if (src, dst) in link_list:
                    graph[src][dst]['bandwidth'] = link_list[(src, dst)][2]
        return graph

    @set_ev_cls(oxp_event.EventOXPTrafficStateChange, MAIN_DISPATCHER)
    def reflesh_bw_graph(self, ev):
        self.graph = self.get_bw_graph(self.graph, self.topology.links)
        self.get_path(self.graph, None, ev.domain.flags)

    def get_path(self, graph, src, flags):
        function = None
        function = setting.function(flags)
        result = get_paths(graph, function, src, self.topology)
        if result:
            self.capabilities = result[0]
            self.paths = result[1]
            return self.paths

        self.logger.debug("Path is not found.")
        return None

    @set_ev_cls(oxp_event.EventOXPLinkDiscovery,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def get_topology(self, ev):
        self.graph = self.get_graph(self.topology.links, self.domains)
        self.get_path(self.graph, None, ev.domain.flags)

    @set_ev_cls(oxp_event.EventOXPTopoReply, MAIN_DISPATCHER)
    def get_path_dict(self, ev):
        self.get_path(self.graph, None, ev.msg.domain.flags)

    def arp_forwarding(self, domain, msg, arp_dst_ip):
        src_domain = domain
        ofproto = msg.datapath.ofproto

        domain_id = self.get_host_location(arp_dst_ip)
        if domain_id:
            # build packet_out pkt and put it into sbp, send to domain
            domain = self.domains[domain_id]
            utils.oxp_send_packet_out(domain, msg,
                                      ofproto.OFPP_CONTROLLER,
                                      ofproto.OFPP_LOCAL)
            return
        else:
            # access info is not existed. send to all UNknow access port
            for domain in self.domains.values():
                if domain == src_domain:
                    continue
                utils.oxp_send_packet_out(domain, msg,
                                          ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPP_LOCAL)

    def shortest_forwarding(self, domain, msg, eth_type, ip_src, ip_dst):
        src_domain = dst_domain = None
        src_domain = self.get_host_location(ip_src)
        dst_domain = self.get_host_location(ip_dst)

        if self.paths:
            if dst_domain:
                path = self.paths[src_domain][dst_domain]
                self.logger.info("Path[%s-->%s]:%s" % (ip_src, ip_dst, path))

                access_table = {}
                for domain_id in self.location.locations:
                    access_table[(domain_id, ofproto_v1_3.OFPP_LOCAL
                                  )] = self.location.locations[domain_id]

                flow_info = (eth_type, ip_src, ip_dst, msg.match['in_port'])
                utils.oxp_install_flow(self.domains, self.topology.links,
                                       access_table, path, flow_info, msg)
        else:
            self.get_topology(None)

    @set_ev_cls(oxp_event.EventOXPSBPPacketIn, MAIN_DISPATCHER)
    def _sbp_packet_in_handler(self, ev):
        msg = ev.msg
        domain = ev.domain
        data = msg.data

        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if isinstance(arp_pkt, arp.arp):
            self.arp_forwarding(domain, msg, arp_pkt.dst_ip)

        if isinstance(ip_pkt, ipv4.ipv4):
            eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
            self.shortest_forwarding(domain, msg, eth_type,
                                     ip_pkt.src, ip_pkt.dst)
        if utils.check_model_is_compressed(domain=domain) and len(data) <= 0:
            eth_type = msg.match['eth_type']
            src = msg.match['ipv4_src']
            dst = msg.match['ipv4_dst']
            self.shortest_forwarding(domain, msg, eth_type, src, dst)
