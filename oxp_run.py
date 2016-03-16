# This file deploy multi ryu controller to work together with OpeneXchange.

import os
import OXP_CFG


USER = OXP_CFG.USER
DOMAINS = OXP_CFG.DOMAINS
DEFAULT_DOMAIN_ID = OXP_CFG.DEFAULT_DOMAIN_ID
OXP_SUPER = OXP_CFG.OXP_SUPER
DEFAULT_OXP_PORT = OXP_CFG.DEFAULT_OXP_PORT
DEFAULT_OFP_PORT = OXP_CFG.DEFAULT_OFP_PORT

os.system("echo '===================Start Super Controller==============='")

# Start OXP Super
os.system("gnome-terminal -t 'Super controller' -x bash -c \
    'ryu-manager ryu.openexchange.super.routing --oxp-role=super \
    --oxp-listen-host=%s --observe-links \
    --ofp-tcp-listen-port=%s >> super_log.txt'" % (OXP_SUPER, DEFAULT_OFP_PORT))


os.system("echo '===================Start Domain Controller==============='")


for domain in DOMAINS:
    # Start domain controller.

    os.system("echo '=====Start Domain Controller %s====='" % (domain))
    os.system("ssh %s@%s 'sudo killall ryu-manager;\
	ryu-manager \
        ryu.openexchange.network.shortest_forwarding \
        --ofp-tcp-listen-port=%s \
        --oxp-role=domain --oxp-domain-id=%s --oxp-server-ip=%s \
        --oxp-server-port=%s \
        --observe-links &' &" % (USER,
                                domain,
                                DEFAULT_OFP_PORT,
                                DEFAULT_DOMAIN_ID,
                                OXP_SUPER,
                                DEFAULT_OXP_PORT))

    DEFAULT_DOMAIN_ID += 1
