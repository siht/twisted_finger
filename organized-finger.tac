# como correr?
# virtual env:
# sudo /your/home/miniconda3/envs/twisted/bin/python /your/home/miniconda3/envs/twisted/bin/twistd -ny organized-finger.tac

# instalación default:
# sudo twistd -ny organized-finger.tac

# los siguientes ejemplos son sugerencia del autor:

# root% twistd -y organized-finger.tac # daemonize, keep pid in twistd.pid
# root% twistd -y organized-finger.tac --pidfile=finger.pid
# root% twistd -y organized-finger.tac --rundir=/
# root% twistd -y organized-finger.tac --chroot=/var
# root% twistd -y organized-finger.tac -l /var/log/finger.log
# root% twistd -y organized-finger.tac --syslog # just log to syslog
# root% twistd -y organized-finger.tac --syslog --prefix=twistedfinger # use given prefix

import sys
sys.path.append('.') # como corre como root no puede encontrar finger

import finger
from twisted.application import (
    internet,
    service,
    strports,
)
from twisted.internet import (
    endpoints,
    reactor,
)
from twisted.spread import pb
from twisted.web import (
    resource,
    server,
)

application = service.Application('finger', uid=1, gid=1)
f = finger.FingerService('/etc/users')
serviceCollection = service.IServiceCollection(application)
f.setServiceParent(serviceCollection)

strports.service('tcp:79', finger.IFingerFactory(f)).setServiceParent(serviceCollection)

site = server.Site(resource.IResource(f))
strports.service('tcp:8000',site,).setServiceParent(serviceCollection)
strports.service('ssl:port=443:certKey=cert.pem:privateKey=key.pem', site).setServiceParent(serviceCollection)

i = finger.IIRCClientFactory(f)
i.nickname = 'fingerbot'
internet.ClientService(endpoints.clientFromString(reactor,'tcp:irc.freenode.org:6667'), i).setServiceParent(serviceCollection)

strports.service('tcp:8889', pb.PBServerFactory(finger.IPerspectiveFinger(f))).setServiceParent(serviceCollection)
