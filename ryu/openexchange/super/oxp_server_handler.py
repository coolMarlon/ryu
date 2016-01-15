"""
This file define the handler of OXP.
Author:www.muzixing.com
"""

"""
Basic OpenExchange handling including negotiation.
"""

import itertools
import logging

import ryu.base.app_manager

from ryu.lib import hub
from ryu import utils
from ryu.openexchange.event import oxp_event
from ryu.openexchange.super.oxp_super import Super_Controller
from ryu.controller import controller
from ryu.controller.handler import set_ev_handler
from ryu.controller.handler import HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER,\
    MAIN_DISPATCHER

from ryu.openexchange import oxproto_v1_0
from ryu.ofproto import ofproto_common, ofproto_parser
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.ofproto import ofproto_v1_0_parser, ofproto_v1_3_parser

from ryu.openexchange.domain import config
from ryu.openexchange.utils.utils import check_mode_is_compressed
from ryu import cfg


# The state transition: HANDSHAKE -> CONFIG -> MAIN
#
# HANDSHAKE: if it receives HELLO message with the valid OXP version,
# sends Features Request message, and moves to CONFIG.
#
# CONFIG: it receives Features Reply message and moves to MAIN
#
# MAIN: it does nothing. Applications are expected to register their
# own handlers.
#
# Note that at any state, when we receive Echo Request message, send
# back Echo Reply message.

CONF = cfg.CONF


class OXP_Server_Handler(ryu.base.app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(OXP_Server_Handler, self).__init__(*args, **kwargs)
        self.name = 'oxp_event'
        self.fake_datapath = None

    def start(self):
        super(OXP_Server_Handler, self).start()
        return hub.spawn(Super_Controller())

    def _hello_failed(self, domain, error_desc):
        self.logger.error(error_desc)
        error_msg = domain.oxproto_parser.OXPErrorMsg(domain)
        error_msg.type = domain.oxproto.OXPET_HELLO_FAILED
        error_msg.code = domain.oxproto.OXPHFC_INCOMPATIBLE
        error_msg.data = error_desc
        domain.send_msg(error_msg)

    @set_ev_handler(oxp_event.EventOXPHello, HANDSHAKE_DISPATCHER)
    def hello_handler(self, ev):
        self.logger.debug('hello ev %s', ev)
        msg = ev.msg
        domain = msg.domain

        # check if received version is supported.
        # pre 1.0 is not supported
        elements = getattr(msg, 'elements', None)
        if elements:
            domain_versions = set()
            for version in itertools.chain.from_iterable(
                    element.versions for element in elements):
                domain_versions.add(version)
            usable_versions = domain_versions & set(
                domain.supported_oxp_version)

            negotiated_versions = set(
                version for version in domain_versions
                if version <= max(domain.supported_oxp_version))
            if negotiated_versions and not usable_versions:
                # Ref:ryu.controller.ofp_handler
                error_desc = (
                    'no compatible version found: '
                    'domain versions %s super version 0x%x, '
                    'the negotiated version is 0x%x, '
                    'but no usable version found. '
                    'If possible, set the domain to use one of OX version %s'
                    % (domain_versions, max(domain.supported_oxp_version),
                       max(negotiated_versions),
                       sorted(domain.supported_oxp_version)))
                self._hello_failed(domain, error_desc)
                return
            if (negotiated_versions and usable_versions and
                    max(negotiated_versions) != max(usable_versions)):
                # Ref:ryu.controller.ofp_handler
                error_desc = (
                    'no compatible version found: '
                    'domain versions 0x%x super version 0x%x, '
                    'the negotiated version is %s but found usable %s. '
                    'If possible, '
                    'set the domain to use one of OX version %s' % (
                        max(domain_versions),
                        max(domain.supported_oxp_version),
                        sorted(negotiated_versions),
                        sorted(usable_versions), sorted(usable_versions)))
                self._hello_failed(domain, error_desc)
                return
        else:
            usable_versions = set(version for version
                                  in domain.supported_oxp_version
                                  if version <= msg.version)
            if (usable_versions and
                max(usable_versions) != min(msg.version,
                                            domain.oxproto.OXP_VERSION)):
                # Ref:ryu.controller.ofp_handler
                version = max(usable_versions)
                error_desc = (
                    'no compatible version found: '
                    'domain 0x%x super 0x%x, but found usable 0x%x. '
                    'If possible, set the domain to use OX version 0x%x' % (
                        msg.version, domain.oxproto.OXP_VERSION,
                        version, version))
                self._hello_failed(domain, error_desc)
                return

        if not usable_versions:
            error_desc = (
                'unsupported version 0x%x. '
                'If possible, set the domain to use one of the versions %s' % (
                    msg.version, sorted(domain.supported_oxp_version)))
            self._hello_failed(domain, error_desc)
            return
        domain.set_version(max(usable_versions))

        features_reqeust = domain.oxproto_parser.OXPFeaturesRequest(domain)
        domain.send_msg(features_reqeust)

        self.logger.debug('move onto config mode')
        domain.set_state(CONFIG_DISPATCHER)

    @set_ev_handler(oxp_event.EventOXPDomainFeatures, CONFIG_DISPATCHER)
    def domain_features_handler(self, ev):
        msg = ev.msg
        domain = msg.domain
        domain.id = msg.domain_id
        domain.sbp_proto_type = msg.proto_type
        domain.sbp_proto_version = msg.sbp_version

        oxproto_parser = domain.oxproto_parser
        self.logger.debug('domain features ev %s', msg)

        get_config_request = oxproto_parser.OXPGetConfigRequest(domain)
        domain.send_msg(get_config_request)

        ev.msg.domain.set_state(MAIN_DISPATCHER)
        # build a fake datapath for parsing OF packet.
        if self.fake_datapath is None:
            self.fake_datapath = controller.Datapath(
                domain.socket, domain.address)

            if domain.sbp_proto_type == oxproto_v1_0.OXPS_OPENFLOW:
                if domain.sbp_proto_version == 4:
                    self.fake_datapath.ofproto = ofproto_v1_3
                    self.fake_datapath.ofproto_parser = ofproto_v1_3_parser
                elif domain.sbp_proto_version == 1:
                    self.fake_datapath.ofproto = ofproto_v1_0
                    self.fake_datapath.ofproto_parser = ofproto_v1_0_parser

    @set_ev_handler(oxp_event.EventOXPEchoRequest,
                    [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def echo_request_handler(self, ev):
        msg = ev.msg
        domain = msg.domain
        echo_reply = domain.oxproto_parser.OXPEchoReply(domain)
        echo_reply.xid = msg.xid
        echo_reply.data = msg.data
        domain.send_msg(echo_reply)

    @set_ev_handler(oxp_event.EventOXPErrorMsg,
                    [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def error_msg_handler(self, ev):
        msg = ev.msg
        self.logger.info('error msg ev %s type 0x%x code 0x%x %s',
                         msg, msg.type, msg.code, utils.hex_array(msg.data))

    @set_ev_handler(oxp_event.EventOXPGetConfigReply,
                    [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def config_reply_handler(self, ev):
        msg = ev.msg
        domain = msg.domain

        domain.flags = msg.flags
        domain.period = msg.period

        domain.miss_send_len = msg.miss_send_len

    def sbp_parser_of_normal(self, domain, datapath, data):
        if domain.sbp_proto_type == oxproto_v1_0.OXPS_OPENFLOW:
            buf = bytearray()
            required_len = ofproto_common.OFP_HEADER_SIZE

            if len(data) == 0:
                return
            buf += data
            while len(buf) >= required_len:
                (version, msg_type, msg_len, xid) = ofproto_parser.header(buf)
                required_len = msg_len
                if len(buf) < required_len:
                    break

                msg = ofproto_parser.msg(datapath, version, msg_type,
                                         msg_len, xid, buf)
                self.logger.debug('ofp msg %s cls %s', msg, msg.__class__)
                if msg:
                    ev = oxp_event.sbp_to_oxp_msg_to_ev(msg)
                    ev.domain = domain
                    self.send_event_to_observers(ev, MAIN_DISPATCHER)

                buf = buf[required_len:]
                required_len = ofproto_common.OFP_HEADER_SIZE

    def sbp_parser_of_compressed(self, domain, datapath, parser, data):
        ofp_parser = datapath.ofproto_parser
        buf = bytearray()
        buf += data
        sbp_header = parser.OXPSBP_Header.parser(buffer(buf), 0)
        msg = None
        default_buffer_id = datapath.ofproto.OFP_NO_BUFFER

        if sbp_header.type == oxproto_v1_0.OXPSBP_FORWARDING_REQUEST:
            # generate a packet_in
            request = parser.OXPSBP_Forwarding_Request.parser(
                buf, oxproto_v1_0.OXP_SBP_COMPRESSED_HEADER_SIZE)
            pkt_data = ''

            if sbp_header.flags == oxproto_v1_0.OXPSBP_FLAGS_CARRY:
                pkt_data = request.data
            if CONF.sbp_proto_type == oxproto_v1_0.OXPS_OPENFLOW:
                match = ofp_parser.OFPMatch(
                    in_port=request.in_port, eth_type=request.eth_type,
                    ipv4_src=request.src_ip, ipv4_dst=request.dst_ip)
                msg = ofp_parser.OFPPacketIn(
                    datapath, buffer_id=default_buffer_id,
                    match=match, data=buffer(pkt_data))
            self.logger.debug('compressed msg %s cls %s', msg, msg.__class__)
        else:
            return None
        if msg:
            ev = oxp_event.sbp_to_oxp_msg_to_ev(msg)
            ev.domain = domain
            self.send_event_to_observers(ev, MAIN_DISPATCHER)

    @set_ev_handler(oxp_event.EventOXPSBP, MAIN_DISPATCHER)
    def SBP_handler(self, ev):
        # Parser the msg and raise an event.
        # Handle event in service or app.
        msg = ev.msg
        domain = msg.domain
        datapath = self.fake_datapath
        data = msg.data
        parser = domain.oxproto_parser

        if check_mode_is_compressed(domain=domain):
            self.sbp_parser_of_compressed(domain, datapath, parser, data)
        else:
            self.sbp_parser_of_normal(domain, datapath, data)
