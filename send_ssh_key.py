import os
import OXP_CFG

# generate ssh key.
os.system('''if [ ! -f ~/.ssh/id_rsa ]  || [ ! -f ~/.ssh/id_rsa.pub ];\
        then ssh-keygen -t rsa; \
        fi''')

USER = OXP_CFG.USER
DOMAINS = OXP_CFG.DOMAINS

for domain in DOMAINS:
    os.system("ssh %s@%s mkdir '.ssh; chmod 700 .ssh'" % (USER, domain))
    os.system(
        "ssh %s@%s 'touch ~/.ssh/authorized_keys;\
        chmod 600 ~/.ssh/authorized_keys'" % (USER, domain))
    os.system("ssh-copy-id %s@%s" % (USER, domain))
