# finger/tap.py
import finger
from twisted.python import usage

class Options(usage.Options):
    optParameters = [
    ['file', 'f', '/etc/users'],
    ['templates', 't', '/usr/share/finger/templates'],
    ['ircnick', 'n', 'fingerbot'],
    ['ircserver', None, 'irc.freenode.net'],
    ['pbport', 'p', 8889],
    ]

    optFlags = [['ssl', 's']]

    def makeService(config):
        return finger.makeService(config)