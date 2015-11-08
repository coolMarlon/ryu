#!/bin/bash

# OXP Configuration.
echo "========================Configuration======================="
DOMAINS=(192.168.0.72
         192.168.0.73
         192.168.0.74)
         #192.168.0.75)
USER=oxp
PASSWD=oxp
OXP_SUPER=192.168.0.71


echo "=====================Start Super Controller================="

#Start OXP Super
gnome-terminal -t "super controller" -x bash -c "ryu-manager ryu.openexchange.super.routing --oxp-role=super --oxp-listen-host=$OXP_SUPER --observe-links --ofp-tcp-listen-port=6653"

# generate ssh key.
ssh-keygen -t rsa


echo "====================Start Domain Controllers================="

length=${#DOMAINS[@]}
for i in $(seq 1 $length);
	do
        # push public key.
        ssh $USER@${DOMAINS[i-1]} "mkdir .ssh; chmod 700 .ssh"
        scp ~/.ssh/id_rsa.pub $USER@${DOMAINS[i-1]}:~/.ssh/id_rsa.pub
        ssh $USER@${DOMAINS[i-1]} "touch ~/.ssh/authorized_keys;
        chmod 600 ~/.ssh/authorized_keys;
        cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys"

        # Send ryu to target vm.
        ssh $USER@${DOMAINS[i-1]} "if ! [ -d /opt/ryu ]; then sudo mkdir /opt/ryu;sudo chown oxp:oxp /opt/ryu; fi"
        scp -r ./* $USER@${DOMAINS[i-1]}:/opt/ryu

        # Install domain controller.
        ssh $USER@${DOMAINS[i-1]} "cd /opt/ryu; sudo python setup.py install"

	# Start domain controller.
	echo "=====================Start domain controller====================="
	ssh $USER@${DOMAINS[i-1]} "ryu-manager ryu.openexchange.network.shortest_forwarding --ofp-tcp-listen-port=6653 --oxp-role=domain --oxp-domain-id=$i --oxp-server-ip=$OXP_SUPER --oxp-server-port=6688 --observe-links & "

	done
