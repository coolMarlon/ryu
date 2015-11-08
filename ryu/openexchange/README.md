#Open eXchange Protocol

Open eXchange Protocol is created by Cheng Li(http://www.muzixing.com).

Open eXchange Protocol(OXP) enable the multi-controller work together.

There are two types of SDN controller:

    * Super Controller(SC)
    * Domain Controller(DC)

###Get OXP

    git clone https://github.com/muzixing/ryu.git

###Pre-install

If you haven't install ryu before, please run pre_install.sh

    sudo bash pre_install.sh

###Install

    sudo ./install.sh

###Configuration

You can config OXP deployment by OXP_CFG.py.

###Implementation

    * create user:group for oxp.
    * sudo permission
        enable use of OXP can using sudo without password. sudo visudo, and add info below.

            oxp ALL=(ALL) NOPASSWD:ALL

    * send ssh public keys

            python send_ssh_key.py

    * Install OXP
        Using git pull is a recommand way. It will be changed soon.

            python oxp_install.py

    * deploy OXP

            python deploy.py

###Test

    You can modify /openexchange/test/multi_network.py to test Open eXchange Protocol.








    

