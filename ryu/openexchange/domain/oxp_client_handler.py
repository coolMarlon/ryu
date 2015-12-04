"""
This file define the handler of OXP.
Author:www.muzixing.com
"""


"""
Basic OpenExchange handling including negotiation.
"""

import itertools
import logging
from ryu.base import app_manager
from ryu.lib import hub
from ryu import utils

from ryu.controller import controller
from ryu.controller.handler import set_ev_handler
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER,\
    MAIN_DISPATCHER, DEAD_DISPATCHER

from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_parser
from ryu.ofproto import ofproto_common

from ryu.openexchange.event import oxp_event
from ryu.openexchange import oxproto_v1_0
from ryu.openexchange import oxproto_v1_0_parser

from ryu.openexchange.domain.oxp_domain import Domain_Controller
from ryu.openexchange.domain import config

from ryu.openexchange.utils.utils import check_model_is_compressed
from ryu.openexchange.utils import utils
from ryu import cfg

CONF = cfg.CONF


# The state transition: HANDSHAKE -> CONFIG -> MAIN
#
# HANDSHAKE: if it receives HELLO message with the valid OFP version,
# sends Features Request message, and moves to CONFIG.
#
# CONFIG: it receives Features Reply message and moves to MAIN
#
# MAIN: it does nothing. Applications are expected to register their
# own handlers.
#
# Note that at any state, when we receive Echo Request message, send
# back Echo Reply message.


class OXP_Client_Handler(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(OXP_Client_Handler, self).__init__(*args, **kwargs)
        self.name = 'oxp_event'
        self.domain = None
        self.oxproto = oxproto_v1_0
        self.oxparser = oxproto_v1_0_parser
        self.network_aware = app_manager.lookup_service_brick("Network_Aware")
        self.fake_datapath = None

    def start(self):
        super(OXP_Client_Handler, self).start()
        self.Domain_Controller = Domain_Controller()

        return hub.spawn(self.Domain_Controller)

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
        # remember domain for asynchronous message.

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

        # now move on to config state
        self.logger.debug('move onto config mode')
        domain.set_state(CONFIG_DISPATCHER)

    @set_ev_handler(oxp_event.EventOXPFeaturesRequest, CONFIG_DISPATCHER)
    def features_request_handler(self, ev):
        msg = ev.msg
        domain = msg.domain
        self.domain = domain

        self.logger.debug('features request ev %s', msg)
        self.oxproto = domain.oxproto
        parser = domain.oxproto_parser
        self.oxparser = parser

        features = self.Domain_Controller.features
        reply = parser.OXPDomainFeatures(domain,
                                         domain_id=features.domain_id,
                                         proto_type=features.proto_type,
                                         sbp_version=features.sbp_version,
                                         capabilities=features.capabilities)
        domain.send_msg(reply)
        ev.msg.domain.set_state(MAIN_DISPATCHER)

    @set_ev_handler(oxp_event.EventOXPErrorMsg,
                    [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def error_msg_handler(self, ev):
        msg = ev.msg
        self.logger.info('error msg ev %s type 0x%x code 0x%x %s',
                         msg, msg.type, msg.code, utils.hex_array(msg.data))

    @set_ev_handler(oxp_event.EventOXPGetConfigRequest,
                    [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def config_request_handler(self, ev):
        msg = ev.msg
        domain = msg.domain

        parser = domain.oxproto_parser
        config = self.Domain_Controller.config

        reply = parser.OXPGetConfigReply(domain,
                                         flags=config.flags,
                                         period=config.period,
                                         miss_send_len=config.miss_send_len)
        domain.send_msg(reply)

    @set_ev_handler(oxp_event.EventOXPSetConfig,
                    [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def set_config_handler(self, ev):
        msg = ev.msg
        domain = msg.domain

        config = self.Domain_Controller.config
        config.set_config(msg.flags, msg.period, msg.miss_send_len)

    @set_ev_cls(oxp_event.EventOXPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        domain = ev.domain
        assert domain is not None
        self.logger.debug(domain)

        if ev.state == MAIN_DISPATCHER:
            self.domain = domain
        elif ev.state == DEAD_DISPATCHER:
            self.logger.debug("connection failed.")
        else:
            pass

    def sbp_parser_of_normal(self, domain, datapath, data):
        if CONF.sbp_proto_type == oxproto_v1_0.OXPS_OPENFLOW:
            buf = bytearray()
            required_len = ofproto_common.OFP_HEADER_SIZE

            if len(data) == 0:
                return
            buf += data
            while len(buf) >= required_len:
                (version, msg_type,
                 msg_len, xid) = ofproto_parser.header(buf)

                required_len = msg_len
                if len(buf) < required_len:
                    break

                msg = ofproto_parser.msg(datapath,
                                         version, msg_type,
                                         msg_len, xid, buf)
                if msg:
                    ev = oxp_event.sbp_to_oxp_msg_to_ev(msg)
                    ev.domain = domain
                    self.send_event_to_observers(ev, MAIN_DISPATCHER)

                buf = buf[required_len:]
                required_len = ofproto_common.OFP_HEADER_SIZE

    def sbp_parser_of_compressed(self, domain, datapath, parser, data):
        ofp_parser = datapath.ofproto_parser
        buf = data
        sbp_header = parser.OXPSBP_Header.parser(buf, 0)
        msg = None
        default_buffer_id = datapath.ofproto.OFP_NO_BUFFER

        if sbp_header.type == oxproto_v1_0.OXPSBP_PACKET_OUT:
            #generate a packet_out event
            sbp_packet_out = parser.OXPSBP_Packet_Out.parser(
                buf, oxproto_v1_0.OXP_SBP_COMPRESSED_HEADER_SIZE)
            if CONF.sbp_proto_type == oxproto_v1_0.OXPS_OPENFLOW:
                msg = utils._build_packet_out(datapath, default_buffer_id,
                                              oxproto_v1_0.OXPP_CONTROLLER,
                                              sbp_packet_out.out_port,
                                              sbp_packet_out.data)
        elif sbp_header.type == oxproto_v1_0.OXPSBP_FORWARDING_REPLY:
            #generate a flow_mod event
            reply = parser.OXPSBP_Forwarding_Reply.parser(
                buf, oxproto_v1_0.OXP_SBP_COMPRESSED_HEADER_SIZE)

            if CONF.sbp_proto_type == oxproto_v1_0.OXPS_OPENFLOW:
                match = ofp_parser.OFPMatch(
                    in_port=reply.src_vport, eth_type=reply.eth_type,
                    ipv4_src=reply.src_ip, ipv4_dst=reply.dst_ip)

                actions = [ofp_parser.OFPActionOutput(reply.dst_vport)]

                msg = utils._build_flow(datapath, 1, match, actions,
                                        idle_timeout=0, hard_timeout=10)
        else:
            return None
        if msg:
            ev = oxp_event.sbp_to_oxp_msg_to_ev(msg)
            ev.domain = domain
            self.send_event_to_observers(ev, MAIN_DISPATCHER)

    @set_ev_handler(oxp_event.EventOXPSBP, MAIN_DISPATCHER)
    def SBP_handler(self, ev):
        msg = ev.msg
        domain = msg.domain
        parser = domain.oxproto_parser
        data = msg.data
        datapath = self.network_aware.fake_datapath

        if check_model_is_compressed():
            self.sbp_parser_of_compressed(domain, datapath, parser, data)
        else:
            self.sbp_parser_of_normal(domain, datapath, data)
