# como correr?
# virtual env:
# sudo /your/home/miniconda3/envs/twisted/bin/python /your/home/miniconda3/envs/twisted/bin/twistd -ny finger.tac
# instalación default:
# sudo twistd -ny finger.tac

# los siguientes ejemplos son sugerencia del autor:

# root% twistd -y finger.tac # daemonize, keep pid in twistd.pid
# root% twistd -y finger.tac --pidfile=finger.pid
# root% twistd -y finger.tac --rundir=/
# root% twistd -y finger.tac --chroot=/var
# root% twistd -y finger.tac -l /var/log/finger.log
# root% twistd -y finger.tac --syslog # just log to syslog
# root% twistd -y finger.tac --syslog --prefix=twistedfinger # use given prefix

import html
from twisted.application import (
    internet,
    service,
    strports,
)
from twisted.internet import (
    defer,
    endpoints,
    protocol,
    reactor,
)
from twisted.protocols import basic
from twisted.web import (
    resource,
    server,
    xmlrpc,
)
from twisted.words.protocols import irc


def catchError(err):
    return 'Internal error in server'


class FingerProtocol(basic.LineReceiver): # a partir de ahora este protocolo es asíncrono
    def lineReceived(self, user): # vamos a usar asincronicidad y el get user nos regresará un objeto Defer
        d = self.factory.getUser(user)
        d.addErrback(catchError) # puedes usar cualquier funcion como callback

        def writeValue(value): # este callback es cuando la información llegue correctamente
            self.transport.write(value + b'\r\n') # le regresamos al cliente la respuesta
            self.transport.loseConnection()
        d.addCallback(writeValue)


class IRCReplyBot(irc.IRCClient):
    def connectionMade(self):
        self.nickname = self.factory.nickname
        irc.IRCClient.connectionMade(self)

    def privmsg(self, user, channel, msg):
        user = user.split('!')[0]
        if self.nickname.lower() == channel.lower():
            d = self.factory.getUser(msg.encode('ascii'))
            d.addErrback(catchError)
            d.addCallback(lambda m: f'Status of {msg}: {m.decode("utf-8")}') # generamos el string
            d.addCallback(lambda m: self.msg(user, m)) # mandamos el string


class UserStatusTree(resource.Resource):
    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service

    def render_GET(self, request):
        d = self.service.getUsers()
        def formatUsers(users):
            l = [f'<li><a href="{user}">{user}</a></li>' for user in users]
            return "<ul>" + "".join(l) + "</ul>"
        d.addCallback(lambda x: [u.decode('utf-8') for u in x])
        d.addCallback(formatUsers)
        d.addCallback(lambda x: bytes(x, 'utf-8'))
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET

    def getChild(self, path, request):
        if path == b"":
            return UserStatusTree(self.service)
        else:
            return UserStatus(path, self.service)


class UserStatus(resource.Resource):
    def __init__(self, user, service):
        resource.Resource.__init__(self)
        self.user = user
        self.service = service

    def render_GET(self, request):
        d = self.service.getUser(self.user)
        d.addCallback(lambda x: x.decode('utf-8'))
        d.addCallback(html.escape)
        d.addCallback(lambda x: bytes(x, 'utf-8'))
        d.addCallback(lambda m: b"<h1>%s</h1>" % self.user + b"<p>%s</p>" % m)
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET

class UserStatusXR(xmlrpc.XMLRPC):
    def __init__(self, service):
        xmlrpc.XMLRPC.__init__(self)
        self.service = service

    def xmlrpc_getUser(self, user):
        return self.service.getUser(user)


class FingerService(service.Service): # ahora puede cargar usuarios de un archivo
    def __init__(self, filename):
        self.users = {}
        self.filename = filename

    def _read(self): # lee archivo cada 30s
        self.users.clear()
        with open(self.filename, 'rb') as f:
            for line in f:
                user, status = line.split(b':', 1)
                user = user.strip()
                status = status.strip()
                self.users[user] = status
        self.call = reactor.callLater(30, self._read)

    def startService(self): # estos métodos ya estaban en service.Service
        self._read()
        service.Service.startService(self)

    def stopService(self): # estos métodos ya estaban en service.Service
        service.Service.stopService(self)
        self.call.cancel()

    def getUser(self, user):
        if isinstance(user, str):
            user = bytes(user, 'utf-8')
        return defer.succeed(self.users.get(user, b'No such user'))

    def getUsers(self):
        return defer.succeed(list(self.users.keys()))

    def getFingerFactory(self):
        f = protocol.ServerFactory()
        f.protocol = FingerProtocol
        f.getUser = self.getUser
        return f

    def getResource(self): # tambien se pueden hacer resources al vuelo
        r = UserStatusTree(self)
        x = UserStatusXR(self)
        r.putChild(b'RPC2', x)
        return r

    def getIRCBot(self, nickname):
        f = protocol.ClientFactory()
        f.protocol = IRCReplyBot
        f.nickname = nickname
        f.getUser = self.getUser
        return f

# asegurate de correr como root este script antes de correr telnet

# telnet localhost 79
# mohsez(o el usuario que esté en tu archivo) [enter]
# web browser
#     -> localhost:8000/
#     -> localhost:8000/user
# IRC
# de preferencia instala tu propio servidor irc.
# con un cliente de IRC:
# entra al canal fingerbot y ahí escribe:
# /msg fingerbot moshez
#
# xml-rpc -> use the fingerXRclient.py

application = service.Application('finger', uid=1, gid=1) # como root
f = FingerService('/etc/users') # pon acá el nombre de un archivo x con -> usuario:mensaje

serviceCollection = service.IServiceCollection(application)
f.setServiceParent(serviceCollection)

strports.service('tcp:79', f.getFingerFactory()).setServiceParent(serviceCollection)
strports.service('tcp:8000', server.Site(f.getResource())).setServiceParent(serviceCollection)
internet.ClientService(
    endpoints.clientFromString(
        reactor, 'tcp:irc.freenode.org:6667' # needs registration, suggest to install own server
    ),
    f.getIRCBot('fingerbot'),
).setServiceParent(serviceCollection)
