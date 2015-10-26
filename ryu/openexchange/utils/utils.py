"""
Define some utils functions.
"""
import logging
from ryu.ofproto.ofproto_v1_3 import OFPP_TABLE
from ryu.openexchange.oxproto_common import OXP_ADVANCED_MODEL
from ryu.openexchange.oxproto_common import OXP_BW_MODEL, OXP_HOP_MODEL
from ryu import cfg


LOG = logging.getLogger('ryu.openexchange.utils')
CONF = cfg.CONF


def check_model_is_advanced():
    if OXP_ADVANCED_MODEL == CONF.oxp_flags & OXP_ADVANCED_MODEL:
        return True
    return False


def check_model_is_bw():
    if OXP_BW_MODEL == CONF.oxp_flags & OXP_BW_MODEL:
        return True
    return False


def check_model_is_hop():
    if OXP_HOP_MODEL == CONF.oxp_flags & OXP_HOP_MODEL:
        return True
    return False


def send_barrier_request(datapath):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    barrier_req = parser.OFPBarrierRequest(datapath=datapath)

    datapath.send_msg(barrier_req)


def _build_flow(dp, p, match, actions, idle_timeout=0, hard_timeout=0):
    ofproto = dp.ofproto
    parser = dp.ofproto_parser

    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    mod = parser.OFPFlowMod(datapath=dp, priority=p,
                            idle_timeout=idle_timeout,
                            hard_timeout=hard_timeout,
                            match=match, instructions=inst)
    return mod


def add_flow(dp, p, match, actions, idle_timeout=0, hard_timeout=0):
    mod = _build_flow(dp, p, match, actions, idle_timeout, hard_timeout)
    dp.send_msg(mod)


def _build_packet_out(datapath, buffer_id, src_port, dst_port, data):
    actions = []
    if dst_port:
        actions.append(datapath.ofproto_parser.OFPActionOutput(dst_port))

    msg_data = None
    if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
        if data is None:
            return None
        msg_data = data

    out = datapath.ofproto_parser.OFPPacketOut(
        datapath=datapath, buffer_id=buffer_id,
        data=msg_data, in_port=src_port, actions=actions)
    return out


def send_packet_out(datapath, buffer_id, src_port, dst_port, data):
    out = _build_packet_out(datapath, buffer_id, src_port, dst_port, data)
    if out:
        datapath.send_msg(out)


def send_flow_mod(datapath, flow_info, src_port, dst_port):
    parser = datapath.ofproto_parser
    actions = []
    actions.append(parser.OFPActionOutput(dst_port))

    match = parser.OFPMatch(
        in_port=src_port, eth_type=flow_info[0],
        ipv4_src=flow_info[1], ipv4_dst=flow_info[2])

    add_flow(datapath, 1, match, actions, idle_timeout=15, hard_timeout=60)


def get_link2port(link_to_port, src_dpid, dst_dpid):
    if (src_dpid, dst_dpid) in link_to_port:
        return link_to_port[(src_dpid, dst_dpid)]
    else:
        LOG.info("dpid:%s->dpid:%s is not in links." % (src_dpid, dst_dpid))
        return None


def get_port(dst_ip, access_table):
    # Domain:access_table: {(sw,port) :(ip, mac)}
    # Super: access_table: {domain, OFP_LOCAL:set(ip, ip1, ip2...)}
    if access_table:
        if isinstance(access_table.values()[0], tuple):
            for key in access_table.keys():
                if dst_ip == access_table[key][0]:
                    dst_port = key[1]
                    return dst_port

        elif isinstance(access_table.values()[0], set):
            for key in access_table.keys():
                if dst_ip in access_table[key]:
                    dst_port = key[1]
                    return dst_port
    return None


def install_flow(datapaths, link2port, access_table, path,
                 flow_info, buffer_id, data, outer_port=None, flag=None):
    ''' path=[dpid1, dpid2, dpid3...]
        flow_info=(eth_type, src_ip, dst_ip, in_port)
        outer_port: port face to other domain.
    '''
    if path is None or len(path) == 0:
        LOG.info("PATH ERROR")
        return
    in_port = flow_info[3]
    first_dp = datapaths[path[0]]
    out_port = first_dp.ofproto.OFPP_LOCAL
    reverse_flow_info = (flow_info[0], flow_info[2], flow_info[1])
    # inter_link
    if len(path) > 2:
        for i in xrange(1, len(path) - 1):
            port = get_link2port(link2port, path[i-1], path[i])
            port_next = get_link2port(link2port, path[i], path[i + 1])
            if port and port_next:
                src_port, dst_port = port[1], port_next[0]
                datapath = datapaths[path[i]]
                send_flow_mod(datapath, flow_info, src_port, dst_port)
                send_flow_mod(datapath, reverse_flow_info, dst_port, src_port)
    if len(path) > 1:
        # the last flow entry: tor -> host
        last_dp = datapaths[path[-1]]
        src_port = get_link2port(link2port, path[-2], path[-1])[1]
        dst_port = get_port(flow_info[2], access_table)
        if dst_port is None:
            assert outer_port
            dst_port = outer_port
        send_flow_mod(last_dp, flow_info, src_port, dst_port)
        send_flow_mod(last_dp, reverse_flow_info, dst_port, src_port)

        # the first flow entry
        port_pair = get_link2port(link2port, path[0], path[1])
        out_port = port_pair[0]
        send_flow_mod(first_dp, flow_info, in_port, out_port)
        send_flow_mod(first_dp, reverse_flow_info, out_port, in_port)
        send_barrier_request(last_dp)
        if flag is None:
            send_packet_out(first_dp, buffer_id, in_port, out_port, data)
            send_packet_out(last_dp, buffer_id, src_port, dst_port, data)
    # src and dst on the same datapath
    else:
        out_port = get_port(flow_info[2], access_table)
        if out_port is None:
            assert outer_port
            out_port = outer_port
        send_flow_mod(first_dp, flow_info, in_port, out_port)
        send_flow_mod(first_dp, reverse_flow_info, out_port, in_port)
        if flag is None:
            send_packet_out(first_dp, buffer_id, in_port, out_port, data)

'''
    Define oxp useful and easy functions below.
'''


def oxp_send_packet_out(domain, msg, src_port, dst_port):
    datapath = msg.datapath
    out = _build_packet_out(
        datapath, datapath.ofproto.OFP_NO_BUFFER, src_port, dst_port, msg.data)
    out.serialize()

    sbp_pkt_out = domain.oxproto_parser.OXPSBP(domain, data=out.buf)
    domain.send_msg(sbp_pkt_out)


def oxp_send_flow_mod(domain, datapath, flow_info, src_port, dst_port):
    parser = datapath.ofproto_parser
    actions = []
    actions.append(parser.OFPActionOutput(dst_port))

    match = parser.OFPMatch(
        in_port=src_port, eth_type=flow_info[0],
        ipv4_src=flow_info[1], ipv4_dst=flow_info[2])

    flow = _build_flow(datapath, 1, match, actions,
                       idle_timeout=10, hard_timeout=30)
    flow.serialize()

    sbp_flow_mod = domain.oxproto_parser.OXPSBP(domain, data=flow.buf)
    domain.send_msg(sbp_flow_mod)


def oxp_install_flow(domains, link2port, access_table,
                     path, flow_info, msg, outer_port=None):
    ''' @path:[dpid1, dpid2 ...]
        @flow_info:(eth_type, src_ip, dst_ip, in_port)
        @outer_port: port face to other domain.
    '''
    if len(path) == 0:
        LOG.info("Path is Empty.")
        return
    in_port = flow_info[3]
    first_node = domains[path[0]]
    out_port = None
    dp = msg.datapath
    # inter_link
    if len(path) > 2:
        for i in xrange(1, len(path) - 1):
            port = get_link2port(link2port, path[i-1], path[i])
            port_next = get_link2port(link2port, path[i], path[i + 1])
            if port and port_next:
                src_port, dst_port = port[1], port_next[0]
                domain = domains[path[i]]
                oxp_send_flow_mod(domain, dp, flow_info, src_port, dst_port)
            else:
                return
    if len(path) > 1:
        # the first flow entry
        port_pair = get_link2port(link2port, path[0], path[1])
        if port_pair is None:
            return
        out_port = port_pair[0]
        # oxp_send_packet_out(first_node, msg, in_port, out_port)
        oxp_send_flow_mod(first_node, dp, flow_info, in_port, out_port)

        # the last flow entry
        last_node = domains[path[-1]]
        port_pair = get_link2port(link2port, path[-2], path[-1])
        if port_pair is None:
            return
        src_port = port_pair[1]
        dst_port = get_port(flow_info[2], access_table)
        if dst_port is None:
            assert outer_port
            dst_port = outer_port
        oxp_send_packet_out(last_node, msg, src_port, dst_port)
        oxp_send_flow_mod(last_node, dp, flow_info, src_port, dst_port)
    else:
        LOG.debug("src and dst in same domain.")
        return
