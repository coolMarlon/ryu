# conding=utf-8
import logging
import struct
import networkx as nx

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet.ether_types import ETH_TYPE_IP
from ryu.openexchange.network import network_aware
from ryu.openexchange.utils import utils
from ryu.ofproto.ofproto_v1_3 import OFPP_TABLE


class Shortest_forwarding(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"Awareness": network_aware.NetworkAwareness}

    def __init__(self, *args, **kwargs):
        super(Shortest_forwarding, self).__init__(*args, **kwargs)
        self.name = 'shortest_forwarding'
        self.awareness = kwargs["Awareness"]
        self.datapaths = self.awareness.datapaths

        # links   :(src_dpid,dst_dpid)->(src_port,dst_port)
        self.link_to_port = self.awareness.link_to_port

        # {sw :[host1_ip,host2_ip,host3_ip,host4_ip]}
        self.access_table = self.awareness.access_table
        self.access_ports = self.awareness.access_ports
        self.outer_ports = self.awareness.outer_ports
        self.abstract = app_manager.lookup_service_brick('oxp_abstract')

    def get_path(self, src, dst):
        if self.abstract is None:
            self.abstract = app_manager.lookup_service_brick('oxp_abstract')
        return self.abstract.get_path(src, dst)

    def flood(self, msg):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dpid in self.awareness.access_ports:
            for port in self.awareness.access_ports[dpid]:
                if (dpid, port) not in self.access_table.keys():
                    datapath = self.datapaths[dpid]
                    out = utils._build_packet_out(
                        datapath, ofproto.OFP_NO_BUFFER,
                        ofproto.OFPP_CONTROLLER, port, msg.data)
                    datapath.send_msg(out)

    def arp_forwarding(self, msg, src_ip, dst_ip):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        result = self.awareness.get_host_location(dst_ip)
        if result:  # host record in access table.
            datapath_dst, out_port = result[0], result[1]
            datapath = self.datapaths[datapath_dst]
            out = utils._build_packet_out(datapath, ofproto.OFP_NO_BUFFER,
                                          ofproto.OFPP_CONTROLLER,
                                          out_port, msg.data)
            datapath.send_msg(out)
        else:
            self.flood(msg)

    def get_sw(self, dpid, in_port, src, dst):
        src_sw = dpid
        dst_sw = None

        src_location = self.awareness.get_host_location(src)
        if in_port in self.access_ports[dpid]:
            if (dpid,  in_port) == src_location:
                src_sw = src_location[0]
            else:
                return None

        dst_location = self.awareness.get_host_location(dst)
        if dst_location:
            dst_sw = dst_location[0]

        return src_sw, dst_sw

    def shortest_forwarding(self, msg, ip_src, ip_dst):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)
        if result:
            src_sw, dst_sw = result[0], result[1]
            if dst_sw:
                path = self.get_path(src_sw, dst_sw)
                self.logger.info("Path[%s-->%s]:%s" % (ip_src, ip_dst, path))
                flow_info = (ETH_TYPE_IP, ip_src, ip_dst, in_port)
                utils.install_flow(self.datapaths, self.link_to_port,
                                   self.access_table, path, flow_info,
                                   msg.buffer_id, msg.data)
                # wait for barrier reply.
                #utils.send_packet_out(self.datapaths[path[0]], msg.buffer_id,
                #                      msg.match['in_port'],
                #                      OFPP_TABLE, msg.data)
        return

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        '''
            In packet_in handler, we need to learn access_table by ARP.
            Therefore, the first packet from UNKOWN host MUST be ARP.
        '''
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if datapath.id in self.outer_ports:
            if in_port in self.outer_ports[datapath.id]:
                # The packet from other domain, MUST ignore it!!
                return

        # We implemente oxp in a big network,
        # so we shouldn't care about the subnet and router.
        if isinstance(arp_pkt, arp.arp):
            self.arp_forwarding(msg, arp_pkt.src_ip, arp_pkt.dst_ip)

        if isinstance(ip_pkt, ipv4.ipv4):
            if len(pkt.get_protocols(ethernet.ethernet)):
                self.shortest_forwarding(msg, ip_pkt.src, ip_pkt.dst)
