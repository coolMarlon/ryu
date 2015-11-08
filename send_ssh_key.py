import os
import OXP_CFG

# generate ssh key.
os.system("ssh-keygen -t rsa")

USER = OXP_CFG.USER
DOMAINS = OXP_CFG.DOMAINS

for domain in DOMAINS:
    os.system("ssh %s@%s mkdir '.ssh; chmod 700 .ssh'" % (USER, domain))
    os.system("scp ~/.ssh/id_rsa.pub %s@%s:~/.ssh/id_rsa.pub" % (USER, domain))
    os.system(
        "ssh %s@%s 'touch ~/.ssh/authorized_keys;\
        chmod 600 ~/.ssh/authorized_keys;\
        cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys'" % (USER, domain))
