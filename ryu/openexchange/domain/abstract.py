"""
Define the community machanism.
Author:www.muzixing.com

Date                Work
2015/7/30           define abstract
2015/8/28           delete features_handler.
"""

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.lib.ip import ipv4_to_bin
from ryu.lib.mac import haddr_to_bin
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER

from ryu.openexchange.event import oxp_event
from ryu.openexchange.network import network_aware
from ryu.openexchange.network import network_monitor
from ryu.openexchange import oxproto_v1_0
from ryu.openexchange import oxproto_v1_0_parser
from ryu.openexchange.oxproto_v1_0 import OXPP_ACTIVE
from ryu.openexchange.oxproto_v1_0 import OXPPS_LIVE
from ryu.openexchange.oxproto_common import OXP_MAX_CAPACITY

from ryu.openexchange.database import topology_data
from ryu.openexchange.domain import setting

from ryu.openexchange.routing_algorithm import routing_algorithm
from ryu.openexchange.utils.controller_id import cap_to_str
from ryu.openexchange.utils.utils import check_model_is_advanced
from ryu.openexchange.utils.utils import check_model_is_bw
from ryu import cfg

CONF = cfg.CONF


class Abstract(app_manager.RyuApp):
    """Abstract complete the network abstract
    and handle the network information update."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
        "Network_Aware": network_aware.Network_Aware,
        "Network_Monitor": network_monitor.Network_Monitor,
    }

    def __init__(self, *args, **kwargs):
        super(Abstract, self).__init__(*args, **kwargs)
        self.name = 'oxp_abstract'
        self.args = args
        self.network = kwargs["Network_Aware"]
        self.monitor = kwargs["Network_Monitor"]
        self.link_to_port = self.network.link_to_port
        self.graph = self.network.graph
        self.access_table = self.network.access_table

        self.free_band_width = self.monitor.free_band_width
        self.domain = app_manager.lookup_service_brick('oxp_event').domain
        self.oxparser = oxproto_v1_0_parser
        self.oxproto = oxproto_v1_0
        self.topology = topology_data.Domain()

        self.capabilities = {}
        self.paths = {}
        self.multi_paths = {}
        self.links = {}

    @set_ev_cls(oxp_event.EventOXPVportStateChange, MAIN_DISPATCHER)
    def vport_handler(self, ev):
        vport_no = ev.vport_no
        state = ev.state
        domain = ev.domain

        reason = None
        if ev.state == OXPPS_LIVE:
            reason = self.oxproto.OXPPR_ADD
        else:
            reason = self.oxproto.OXPPR_DELETE

        vport = self.oxparser.OXPVPort(vport_no=vport_no, state=state)
        vport_state_change = self.oxparser.OXPVportStatus(
            domain, vport=vport, reason=reason)
        domain.send_msg(vport_state_change)

    @set_ev_cls(oxp_event.EventOXPHostStateChange, MAIN_DISPATCHER)
    def host_update_handler(self, ev):
        domain = ev.domain
        hosts = []
        for host in ev.hosts:
            h = self.oxparser.OXPHost(ip=ipv4_to_bin(host[0]),
                                      mac=haddr_to_bin(host[1]),
                                      mask=255, state=host[2])
            hosts.append(h)
        host_update = self.oxparser.OXPHostUpdate(domain, hosts)
        domain.send_msg(host_update)

    @set_ev_cls(oxp_event.EventOXPHostRequest, MAIN_DISPATCHER)
    def host_request_handler(self, ev):
        domain = ev.msg.domain
        host_info = self.access_table
        hosts = []
        for key in host_info:
            h = self.oxparser.OXPHost(ip=ipv4_to_bin(host_info[key][0]),
                                      mac=haddr_to_bin(host_info[key][1]),
                                      mask=255, state=OXPP_ACTIVE)
            hosts.append(h)
        host_reply = self.oxparser.OXPHostReply(domain, hosts)
        domain.send_msg(host_reply)

    def create_links_bw(self, vport=[], capabilities={}):
        links = []
        for src in vport:
            src_dpid, src_port_no = self.network.vport[src]
            cap = OXP_MAX_CAPACITY
            if src_dpid in self.free_band_width:
                if src_port_no in self.free_band_width[src_dpid]:
                    cap = self.free_band_width[src_dpid][src_port_no]

            link = self.oxparser.OXPInternallink(
                src_vport=int(src), dst_vport=int(src),
                capability=cap_to_str(cap))
            links.append(link)

            if check_model_is_advanced():
                for dst in vport:
                    if src > dst:
                        src_dpid, src_port_no = self.network.vport[src]
                        dst_dpid, dst_port_no = self.network.vport[dst]
                        if src_dpid in capabilities:
                            if dst_dpid in capabilities[src_dpid]:
                                cap = capabilities[src_dpid][dst_dpid]
                            else:
                                self.logger.debug("%s not in capa[%s]" % (
                                    dst_dpid, src_dpid))
                                continue
                        else:
                            self.logger.debug(
                                "%s not in capabilities" % src_dpid)
                            continue
                        link = self.oxparser.OXPInternallink(
                            src_vport=int(src), dst_vport=int(dst),
                            capability=cap_to_str(cap))
                        links.append(link)
        return links

    def create_links(self, vport=[], capabilities={}):
        links = []
        for src in vport:
            for dst in vport:
                if src > dst:
                    src_dpid, src_port_no = self.network.vport[src]
                    dst_dpid, dst_port_no = self.network.vport[dst]
                    if src_dpid in capabilities:
                        if dst_dpid in capabilities[src_dpid]:
                            cap = capabilities[src_dpid][dst_dpid]
                        else:
                            self.logger.debug("%s not in capa[%s]" % (
                                dst_dpid, src_dpid))
                            continue
                    else:
                        self.logger.debug("%s not in capabilities" % src_dpid)
                        continue
                    link = self.oxparser.OXPInternallink(
                        src_vport=int(src), dst_vport=int(dst),
                        capability=cap_to_str(cap))
                    links.append(link)
        return links

    def create_bw_graph(self, graph, link2port, bw_dict):
        for link in link2port:
            (src_dpid, dst_dpid) = link
            (src_port, dst_port) = link2port[link]

            if src_dpid in bw_dict and dst_dpid in bw_dict:
                bw_src = bw_dict[src_dpid][src_port]
                bw_dst = bw_dict[dst_dpid][dst_port]
                graph[src_dpid][dst_dpid]['bandwidth'] = min(bw_src, bw_dst)
            else:
                graph[src_dpid][dst_dpid]['bandwidth'] = 0
        return graph

    @set_ev_cls(oxp_event.EventOXPTrafficStateChange, MAIN_DISPATCHER)
    def reflesh_bw_best_path(self, ev):
        self.free_band_width = ev.traffic
        self.graph = self.create_bw_graph(
            self.graph, self.link_to_port, self.free_band_width)

        capabilities, best_paths = routing_algorithm.band_width_compare(
            self.graph, self.multi_paths, self.paths)

        self.capabilities = capabilities
        self.paths = best_paths
        if self.domain is None:
            self.domain = app_manager.lookup_service_brick('oxp_event').domain
        self.topo_reply(self.domain)

    def get_path(self, src, dst):
        if src in self.paths:
            if dst in self.paths[src]:
                return self.paths[src][dst]
        self.logger.debug("Path is not found.")
        return None

    @set_ev_cls(oxp_event.EventOXPTopoStateChange, MAIN_DISPATCHER)
    def create_paths(self, ev):
        graph = ev.topo
        function = setting.function(CONF.oxp_flags)
        if check_model_is_bw():
            self.graph = self.create_bw_graph(graph, self.link_to_port,
                                              self.free_band_width)
        result = routing_algorithm.get_paths(graph, function)
        if result:
            self.capabilities = result[0]
            self.paths = result[1]
            if check_model_is_bw():
                self.multi_paths = result[2]
            return self.paths
        self.logger.debug("Path is not found.")
        return None

    def get_link_capabilities(self):
        self.topology.ports = self.network.vport.keys()
        if len(self.topology.ports):
            self.topology.capabilities = self.capabilities
            self.topology.paths = self.paths

            links = []
            if check_model_is_bw():
                links = self.create_links_bw(self.topology.ports,
                                             self.capabilities)
            else:
                if check_model_is_advanced():
                    links = self.create_links(self.topology.ports,
                                              self.capabilities)
            return links
        return None

    def topo_reply(self, domain):
        self.links = self.get_link_capabilities()
        topo_reply = self.oxparser.OXPTopoReply(domain, links=self.links)
        domain.send_msg(topo_reply)

    @set_ev_cls(oxp_event.EventOXPTopoRequest, MAIN_DISPATCHER)
    def topo_request_handler(self, ev):
        if check_model_is_advanced():
            domain = ev.msg.domain
            self.topology.domain_id = domain.id
            self.oxproto = domain.oxproto
            self.oxparser = domain.oxproto_parser

            self.topo_reply(domain)

    @set_ev_cls(oxp_event.EventOXPSBPPacketIn, MAIN_DISPATCHER)
    def sbp_packet_in_handler(self, ev):
        msg = ev.msg
        msg.serialize()
        if self.domain is None:
            self.domain = app_manager.lookup_service_brick('oxp_event').domain

        sbp_pkt = self.oxparser.OXPSBP(self.domain, data=msg.buf)
        self.domain.send_msg(sbp_pkt)
        return
