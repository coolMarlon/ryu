"""
Reply Topo data to super periodically.
Author:www.muzixing.com

Date                Work
2015/8/3            define topo reply

"""
from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER

from ryu.openexchange.network import network_aware
from ryu.openexchange.event import oxp_event
from ryu.openexchange.oxproto_common import OXP_MAX_PERIOD
from ryu.openexchange.database import topology_data
from ryu.openexchange.utils.controller_id import cap_to_str
from ryu.openexchange.utils.utils import check_model_is_advanced
from ryu.openexchange.utils.utils import check_model_is_bw
from ryu import cfg
from ryu.lib import hub

CONF = cfg.CONF


class TopoReply(app_manager.RyuApp):
    """TopoReply complete periodical topo reply."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {"Network_Aware": network_aware.Network_Aware}

    def __init__(self, *args, **kwargs):
        super(TopoReply, self).__init__(*args, **kwargs)
        self.name = 'oxp_toporeply'
        self.args = args
        self.network = kwargs["Network_Aware"]
        self.domain = None
        self.oxparser = None
        self.topology = topology_data.Domain()
        self.abstract = app_manager.lookup_service_brick('oxp_abstract')
        self.monitor_thread = hub.spawn(self._monitor)
        self.links = []

    def _monitor(self):
        while True and check_model_is_advanced():
            if self.domain is not None:
                self.topo_reply()
            hub.sleep(CONF.oxp_period)

    @set_ev_cls(oxp_event.EventOXPTopoRequest, MAIN_DISPATCHER)
    def topo_request_handler(self, ev):
        msg = ev.msg
        self.domain = msg.domain
        self.topology.domain_id = self.domain.id
        self.oxparser = self.domain.oxproto_parser

    def get_link_capabilities(self):
        if self.abstract is None:
            self.abstract = app_manager.lookup_service_brick('oxp_abstract')
        return self.abstract.get_link_capabilities()
        self.topology.ports = self.network.vport.keys()

    def topo_reply(self):
        links = self.get_link_capabilities()
        if links == self.links:
            if CONF.oxp_period < OXP_MAX_PERIOD:
                CONF.oxp_period += 1
            else:
                CONF.oxp_period = OXP_MAX_PERIOD
        else:
            self.links = links
            if self.domain:
                topo_reply = self.oxparser.OXPTopoReply(self.domain,
                                                        links=links)
                self.domain.send_msg(topo_reply)
