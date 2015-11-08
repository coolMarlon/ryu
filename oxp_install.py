import os
import OXP_CFG


USER = OXP_CFG.USER
DOMAINS = OXP_CFG.DOMAINS

# Using Git is a recommand way.
# os.system('git add *;git commit -am "commit for deploy"; git push')


for domain in DOMAINS:
    os.system("ssh %s@%s 'if ! [ -d /opt/ryu ];\
        then sudo mkdir /opt/ryu;sudo chown oxp:oxp /opt/ryu; \
        fi' " % (USER, domain))
    #os.system("ssh %s@%s 'cd /opt/ryu; git pull\
    #    sudo python setup.py install'" % (USER, domain))

    os.system("scp -r ./* %s@%s:/opt/ryu" % (USER, domain))
    os.system("ssh %s@%s 'cd /opt/ryu; \
        sudo python setup.py install'" % (USER, domain))
