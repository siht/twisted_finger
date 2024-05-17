# como correr?
# virtual env:
# sudo /your/home/miniconda3/envs/twisted/bin/python /your/home/miniconda3/envs/twisted/bin/twistd -ny simple-finger.tac

# instalación default:
# sudo twistd -ny simple-finger.tac

# los siguientes ejemplos son sugerencia del autor:

# root% twistd -y simple-finger.tac # daemonize, keep pid in twistd.pid
# root% twistd -y simple-finger.tac --pidfile=finger.pid
# root% twistd -y simple-finger.tac --rundir=/
# root% twistd -y simple-finger.tac --chroot=/var
# root% twistd -y simple-finger.tac -l /var/log/finger.log
# root% twistd -y simple-finger.tac --syslog # just log to syslog
# root% twistd -y simple-finger.tac --syslog --prefix=twistedfinger # use given prefix

import sys
sys.path.append('.') # como corre como root no puede encontrar finger

import finger
from twisted.application import service
options = {
    'file': '/etc/users',
    'templates': '/usr/share/finger/templates',
    'ircnick': 'fingerbot',
    'ircserver': 'irc.freenode.net',
    'pbport': 8889,
    'ssl': 'ssl=0',
}
ser = finger.makeService(options)
application = service.Application('finger', uid=1, gid=1)
ser.setServiceParent(service.IServiceCollection(application))
