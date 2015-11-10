#!/usr/bin/python

"""
    This example create 7 sub-networks to connect 7 domain controllers.
    Each domain network contains at least 5 switches.
    For an easy test, we add 2 hosts per switch.

    So, in our topology, we have at least 35 switches and 70 hosts.
    Hope it will work perfectly.

"""

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo
import logging
import os


def multiControllerNet(con_num=7, pod=4, density=2):
    "Create a network from semi-scratch with multiple controllers."
    controller_list = []
    switch_list = []
    host_list = []

    CoreLayerSwitch = (pod/2)**2
    AggLayerSwitch = pod*pod/2
    EdgeLayerSwitch = pod*pod/2

    domain_sw_num = CoreLayerSwitch + 2 * AggLayerSwitch
    sw_num = domain_sw_num * con_num
    host_num = EdgeLayerSwitch * density * con_num

    bw_c2a = 0.2
    bw_a2e = 0.1
    bw_h2a = 0.5

    # create network.
    logger = logging.getLogger('ryu.openexchange.test.multi_network')

    net = Mininet(controller=None,
                  switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    # add controllers.
    for i in xrange(con_num):
        name = 'controller%s' % str(i)
        c = net.addController(name, controller=RemoteController,
                              port=6661 + i)
        controller_list.append(c)
        logger.debug("*** Creating %s" % name)

    # add switches.
    logger.debug("*** Creating switches")
    switch_list = [net.addSwitch('s%d' % n) for n in xrange(1, int(sw_num)+1)]

    # add hosts
    logger.debug("*** Creating hosts")
    host_list = [net.addHost('h%d' % n) for n in xrange(host_num)]
    print "length of hosts: ", len(host_list)

    """
    logger.debug("*** Creating links of host2switch.")
    for i in xrange(0, sw_num):
        net.addLink(switch_list[i], host_list[i*2])
        net.addLink(switch_list[i], host_list[i*2+1])


    def createLink(self, bw_c2a=0.2, bw_a2e=0.1, bw_h2a=0.5):
        logger.debug("Add link Core to Agg.")
        end = pod/2
        for x in xrange(0, AggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    net.addLink(
                        self.CoreSwitchList[i*end+j],
                        self.AggSwitchList[x+i],
                        bw=bw_c2a)

        logger.debug("Add link Agg to Edge.")
        for x in xrange(0, self.iAggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    self.addLink(
                        self.AggSwitchList[x+i], self.EdgeSwitchList[x+j],
                        bw=bw_a2e)

        logger.debug("Add link Edge to Host.")
        for x in xrange(0, self.iEdgeLayerSwitch):
            for i in xrange(0, self.density):
                self.addLink(
                    self.EdgeSwitchList[x],
                    self.HostList[self.density * x + i],
                    bw=bw_h2a)
    """
    # add links
    logger.debug("*** Creating interior links of switch2switch.")
    host_index = 0
    for n in xrange(0, sw_num, sw_num/con_num):
        # create a fattree.
        end = pod/2
        for x in xrange(0, AggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    net.addLink(
                        switch_list[n+i*end+j],
                        switch_list[n+CoreLayerSwitch+x+i],
                        bw=bw_c2a)

        logger.debug("Add link Agg to Edge.")
        for x in xrange(0, AggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    net.addLink(
                        switch_list[n+CoreLayerSwitch+x+i],
                        switch_list[n+CoreLayerSwitch+AggLayerSwitch+x+j],
                        bw=bw_a2e)

        logger.debug("Add link Edge to Host.")
        for x in xrange(0, EdgeLayerSwitch):
            for i in xrange(0, density):
                print host_index
                net.addLink(
                    switch_list[n+CoreLayerSwitch+AggLayerSwitch+x],
                    host_list[host_index],
                    bw=bw_h2a)
                host_index += 1

    logger.debug("*** Creating intra links of switch2switch.")

    #for i in xrange(con_num):
    net.addLink(switch_list[0], switch_list[domain_sw_num+1])
    net.addLink(switch_list[1], switch_list[domain_sw_num*2+2])

    net.addLink(switch_list[domain_sw_num+1], switch_list[domain_sw_num*2+1])
    net.addLink(switch_list[domain_sw_num+2], switch_list[domain_sw_num*3+2])

    net.addLink(switch_list[domain_sw_num*3+2], switch_list[domain_sw_num*2+1])
    net.addLink(switch_list[domain_sw_num*3+2], switch_list[domain_sw_num*4+1])

    net.addLink(switch_list[domain_sw_num*4+1], switch_list[domain_sw_num*5+2])
    net.addLink(switch_list[domain_sw_num*4+2], switch_list[domain_sw_num*6+1])

    net.addLink(switch_list[domain_sw_num*5+1], switch_list[domain_sw_num*6+1])
    net.addLink(switch_list[domain_sw_num*5+2], switch_list[domain_sw_num*6+2])

    """
    # 0-4  5-9 10-14 15-19 20-24 25-29 30-34
    # domain1 -> others
    net.addLink(switch_list[4], switch_list[6])
    net.addLink(switch_list[4], switch_list[10])
    net.addLink(switch_list[1], switch_list[20])

    # domain2 -> others
    net.addLink(switch_list[6], switch_list[10])
    net.addLink(switch_list[8], switch_list[12])
    net.addLink(switch_list[7], switch_list[25])

    # domain3 -> others
    net.addLink(switch_list[10], switch_list[16])
    net.addLink(switch_list[12], switch_list[16])
    net.addLink(switch_list[12], switch_list[27])

    # domain4 -> others
    net.addLink(switch_list[16], switch_list[21])
    net.addLink(switch_list[18], switch_list[27])
    net.addLink(switch_list[19], switch_list[34])

    # domain5 -> others
    net.addLink(switch_list[21], switch_list[27])
    net.addLink(switch_list[23], switch_list[31])

    # domain6 -> others
    net.addLink(switch_list[25], switch_list[31])
    net.addLink(switch_list[27], switch_list[32])

    #domain7 has not need to add links.
    """

    net.build()
    for c in controller_list:
        c.start()

    _No = 0
    for i in xrange(0, sw_num, sw_num/con_num):
        for j in xrange(sw_num/con_num):
            switch_list[i+j].start([controller_list[_No]])
        _No += 1

    logger.info("*** Setting OpenFlow version")

    for sw in switch_list:
        cmd = "sudo ovs-vsctl set bridge %s protocols=OpenFlow13" % sw
        os.system(cmd)

    logger.info("*** Running CLI")
    CLI(net)

    logger.info("*** Stopping network")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    multiControllerNet(con_num=7, pod=4, density=2)
