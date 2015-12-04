"""
Translate Packet_out and Flow_mod.
Author:www.muzixing.com

Date                Work
2015/9/1            new Translation.
"""

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.openexchange.event import oxp_event
from ryu.openexchange.utils import utils
from ryu.ofproto.ofproto_v1_3 import OFPP_TABLE


class Translation(app_manager.RyuApp):
    """Translation module translate the Packet_out and Flow_mod from super."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Translation, self).__init__(*args, **kwargs)
        self.name = 'oxp_translation'
        self.network = app_manager.lookup_service_brick("Network_Aware")
        self.abstract = app_manager.lookup_service_brick('oxp_abstract')
        self.buffer = {}
        self.buffer_id = 0
        self.outer_hosts = set()
        self.datapaths = self.network.datapaths
        self.access_table = self.network.access_table

    def flood(self, msg):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dpid in self.network.access_ports:
            for port in self.network.access_ports[dpid]:
                if (dpid, port) not in self.access_table.keys():
                    datapath = self.datapaths[dpid]
                    out = utils._build_packet_out(
                        datapath, ofproto.OFP_NO_BUFFER,
                        ofproto.OFPP_CONTROLLER, port, msg.data)
                    datapath.send_msg(out)

    def oxp_arp_forwarding(self, msg, src_ip, dst_ip):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # packet_out from super, record src.
        self.outer_hosts.add(src_ip)

        # dst in domain
        result = self.network.get_host_location(dst_ip)
        if result:
            #src from other domain, send to host
            datapath_dst, out_port = result[0], result[1]
            datapath = self.datapaths[datapath_dst]
            out = utils._build_packet_out(datapath, ofproto.OFP_NO_BUFFER,
                                          ofproto.OFPP_CONTROLLER,
                                          out_port, msg.data)
            datapath.send_msg(out)
        else:
            self.flood(msg)

    @set_ev_cls(oxp_event.EventOXPSBPPacketOut, MAIN_DISPATCHER)
    def sbp_packet_out_handler(self, ev):
        msg = ev.msg
        domain = ev.domain

        pkt = packet.Packet(buffer(msg.data))
        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype

        if msg.actions[0].port == ofproto_v1_3.OFPP_LOCAL:
            if isinstance(arp_pkt, arp.arp):
                self.oxp_arp_forwarding(msg, arp_pkt.src_ip, arp_pkt.dst_ip)
            #save msg.data for flow_mod.
            elif isinstance(ip_pkt, ipv4.ipv4):
                self.buffer[(eth_type, ip_pkt.src, ip_pkt.dst)] = msg.data
        else:
            # packet_out to datapath:port.
            vport = msg.actions[0].port
            dpid, port = self.network.vport[vport]
            datapath = self.network.datapaths[dpid]
            ofproto = datapath.ofproto
            out = utils._build_packet_out(datapath, ofproto.OFP_NO_BUFFER,
                                          ofproto.OFPP_CONTROLLER,
                                          port, msg.data)
            #save msg.data for flow_mod.
            if isinstance(ip_pkt, ipv4.ipv4):
                self.buffer[(eth_type, ip_pkt.src, ip_pkt.dst)] = msg.data
            # if super just send a pkt_out, domain need to send it.
            datapath.send_msg(out)

    def shortest_forwarding(self, msg, eth_type, ip_src, ip_dst):
        ofproto = msg.datapath.ofproto
        parser = msg.datapath.ofproto_parser
        src_sw = dst_sw = outer_port = data = flag = None
        in_port = msg.match['in_port']

        src_location = self.network.get_host_location(ip_src)
        dst_location = self.network.get_host_location(ip_dst)
        if src_location:
            src_sw, in_port = src_location
        else:
            src_sw, in_port = self.network.vport[in_port]
        if dst_location:
            dst_sw = dst_location[0]
        else:
            for i in msg.instructions:
                if isinstance(i, parser.OFPInstructionActions):
                    for action in i.actions:
                        if isinstance(action, parser.OFPActionOutput):
                            vport = action.port
                            dst_sw, outer_port = self.network.vport[vport]
                            break
        if self.abstract.paths:
            if dst_sw:
                path = self.abstract.get_path(src_sw, dst_sw)
                self.logger.debug(
                    " PATH[%s --> %s]:%s" % (ip_src, ip_dst, path))

                flow_info = (eth_type, ip_src, ip_dst, in_port)
                _key = (eth_type, ip_src, ip_dst)
                if utils.check_model_is_compressed():
                    if _key in self.abstract.buffer:
                        data_list = self.abstract.buffer[_key]
                        if len(data_list) > 0:
                            data = data_list.pop(0)
                    else:
                        flag = True
                else:
                    if _key in self.buffer:
                        data = self.buffer[_key]
                        del self.buffer[_key]
                    else:
                        flag = True
                utils.install_flow(self.datapaths,
                                   self.network.link_to_port,
                                   self.network.access_table, path, flow_info,
                                   ofproto.OFP_NO_BUFFER, data,
                                   outer_port=outer_port, flag=flag)
                # waiting for barrier reply logic.
                #utils.send_packet_out(self.datapaths[path[0]], msg.buffer_id,
                #                      msg.match['in_port'], OFPP_TABLE, data)
        else:
            self.network.get_topology(None)

    @set_ev_cls(oxp_event.EventOXPSBPFlowMod, MAIN_DISPATCHER)
    def sbp_flow_mod_handler(self, ev):
        msg = ev.msg
        domain = ev.domain

        ip_src = msg.match['ipv4_src']
        ip_dst = msg.match['ipv4_dst']
        eth_type = msg.match['eth_type']

        self.shortest_forwarding(msg, eth_type, ip_src, ip_dst)
