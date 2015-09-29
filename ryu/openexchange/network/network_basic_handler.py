# conding=utf-8
import logging
import struct
import networkx as nx

from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp

from ryu.openexchange.network import network_aware


class Network_Basic_Handler(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"Network_Aware": network_aware.Network_Aware}

    def __init__(self, *args, **kwargs):
        super(Network_Basic_Handler, self).__init__(*args, **kwargs)
        self.name = 'network_basic_handler'
        self.network_aware = kwargs["Network_Aware"]
        self.outer_ports = self.network_aware.outer_ports
        self.translation = lookup_service_brick('oxp_translation')

    def outer_arp_handler(self, msg, src_ip, dst_ip):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # dst in other domain, send to super and return.
        result = self.network_aware.get_host_location(dst_ip)
        if self.translation is None:
            self.translation = lookup_service_brick('oxp_translation')
        if dst_ip in self.translation.outer_hosts or result is None:
            self.network_aware.raise_sbp_packet_in_event(
                msg, ofproto_v1_3.OFPP_LOCAL, msg.data)

    def outer_domain_pkt_handler(self, msg, eth_type, ip_src, ip_dst):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        src_sw = dst_sw = None

        src_location = self.network_aware.get_host_location(ip_src)
        dst_location = self.network_aware.get_host_location(ip_dst)
        if src_location:
            src_sw = src_location[0]
        else:
            # src doesn't belong to domain, ignore it.
            return
        if dst_location:
            dst_sw = dst_location[0]

        if dst_sw is None:
            # dst is not in domian,raise sbp event.
            if isinstance(msg, parser.OFPPacketIn):
                self.network_aware.raise_sbp_packet_in_event(
                    msg, ofproto_v1_3.OFPP_LOCAL, msg.data)

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
            self.outer_arp_handler(msg, arp_pkt.src_ip, arp_pkt.dst_ip)

        if isinstance(ip_pkt, ipv4.ipv4):
            if len(pkt.get_protocols(ethernet.ethernet)):
                eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
                self.outer_domain_pkt_handler(msg, eth_type, ip_pkt.src,
                                              ip_pkt.dst)
