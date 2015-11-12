"""
This file define the topology's data structure.
Author:www.muzixing.com


Link:((src_domain, dst_domain), (src_port, dst_port)): capacity

If src_domain == dst_domain, the link will be an interallink.
esle, it is an intralink.

"""
from . import data_base
from ryu.openexchange import oxproto_v1_0
from ryu.openexchange.utils.utils import check_model_is_bw
from ryu import cfg

CONF = cfg.CONF


class Domain(data_base.DataBase):
    """
        class Topo describe the link and vport of domain network
        @args:  domain_id = domain id
                link is the link from msg.

                self.links: {
                    (src_port, dst_port): capabilities,
                    ...
                    }

                paths: domain usage, save the intralinks' paths.
                capabilities:domain usage, save the capabilities of intralinks.
    """
    def __init__(self, domain_id=None, links={},
                 ports=set(), paths={}, capabilities={}):
        self.domain_id = domain_id
        self.links = links
        self.ports = ports

        self.paths = paths
        self.capabilities = capabilities

    def __call__(self):
        self.get_links(self.links)

    def get_links(self, links):
        return self.links

    def update_port(self, msg):
        if msg.reason == oxproto_v1_0.OXPPR_ADD:
            self.ports.add((msg.vport_no, msg.state))
        elif msg.reason == oxproto_v1_0.OXPPR_DELETE:
            self.ports.remove((msg.vport_no, msg.state))
            for key in self.links.keys():
                if msg.vport_no in key:
                    del self.links[key]

    def update_link(self, links):
        for i in links:
            capability = int(i.capability, 16)   # Default way.
            self.links[(i.src_vport, i.dst_vport)] = capability
            self.links[(i.dst_vport, i.src_vport)] = capability

            self.ports.add((i.src_vport, oxproto_v1_0.OXPPS_LIVE))
            self.ports.add((i.dst_vport, oxproto_v1_0.OXPPS_LIVE))
        print "domain:", self.domain_id, self.links
        return self.links


class Super_Topo(data_base.DataBase):
    """
        class Topo describe the domains and inter-links of full networks

        @args:  domains: {id:domain, }
                links: {
                    (src_domain, dst_domain):(src_port, dst_port, capacity),
                    ...
                        }
                links is inter-links.
    """

    def __init__(self, domains={}, links={}):
        self.domains = domains
        self.links = links

    def get_domain(self, domain_id):
        return self.domains[domain_id]

    def get_topo(self):
        return self.domains, self.links

    def update_link(self, link):
        self.links.update(link)

    def update_port(self, msg):
        domain = msg.domain
        if domain.id in self.domains:
            # update intra-links
            self.domains[domain.id].update_port(msg)

            # update inter-links
            if msg.reason == oxproto_v1_0.OXPPR_DELETE:
                for key in self.links.keys():
                    vport = [(key[0], self.links[key][0]),
                             (key[1], self.links[key][1])]
                    if (msg.domain.id, msg.vport_no) in vport:
                        del self.links[key]

    def delete_domain(self, domain):
        if domain in self.domains:
            self.domains.remove(domain)

    def refresh_inter_links_capabilities(self):
        if check_model_is_bw():
            # reflesh the inter-links' bandwidth.
            # bug!!! error bw data.

            for domain in self.domains.values():
                print "doid: ", domain.domain_id, domain.links

            for link in self.links:
                src, dst = link
                src_port, dst_port, cap = self.links[link]
                if (src_port, src_port) in self.domains[src].links:
                    if (dst_port, dst_port) in self.domains[dst].links:
                        bw_src = self.domains[src].links[(src_port, src_port)]
                        bw_dst = self.domains[dst].links[(dst_port, dst_port)]
                        min_bw = min(bw_src, bw_dst)
                        self.links[link] = (src_port, dst_port, min_bw)
