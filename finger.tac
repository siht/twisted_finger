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
from zope.interface import (
    Interface,
    implementer,
)
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
from twisted.python import components
from twisted.web import (
    resource,
    server,
    xmlrpc,
)
from twisted.words.protocols import irc


def str2bytes(string):
    return bytes(string, 'utf-8')


def bytes2str(bbytes):
    return bbytes.decode('utf-8')


class IFingerService(Interface):
    def getUser(user):
        '''
        Return a deferred returning L{bytes}.
        '''

    def getUsers():
        '''
        Return a deferred returning a L{list} of L{bytes}.
        '''


class IFingerSetterService(Interface):
    def setUser(user, status):
        '''
        Set the user's status to something.
        '''


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


class IFingerFactory(Interface):
    def getUser(user):
        '''
        Return a deferred returning L{bytes}
        '''

    def buildProtocol(addr):
        '''
        Return a protocol returning L{bytes}
        '''


@implementer(IFingerFactory)
class FingerFactoryFromService(protocol.ServerFactory):
    protocol = FingerProtocol

    def __init__(self, service):
        self.service = service

    def getUser(self, user):
        return self.service.getUser(user)

components.registerAdapter(FingerFactoryFromService, IFingerService, IFingerFactory)


class FingerSetterProtocol(basic.LineReceiver):
    def connectionMade(self):
        self.lines = []

    def lineReceived(self, line):
        self.lines.append(line)

    def connectionLost(self, reason):
        if len(self.lines) == 2:
            self.factory.setUser(*self.lines)


class IFingerSetterFactory(Interface):
    def setUser(user, status):
        '''
        Return a deferred returning L{bytes}.
        '''

    def buildProtocol(addr):
        '''
        Return a protocol returning L{bytes}.
        '''


@implementer(IFingerSetterFactory)
class FingerSetterFactoryFromService(protocol.ServerFactory):
    protocol = FingerSetterProtocol

    def __init__(self, service):
        self.service = service

    def setUser(self, user, status):
        self.service.setUser(user, status)

components.registerAdapter(
    FingerSetterFactoryFromService, IFingerSetterService, IFingerSetterFactory
)


class IRCReplyBot(irc.IRCClient):
    def connectionMade(self):
        self.nickname = self.factory.nickname
        irc.IRCClient.connectionMade(self)

    def privmsg(self, user, channel, msg):
        user = user.split('!')[0]
        if self.nickname.lower() == channel.lower():
            d = self.factory.getUser(msg.encode('ascii'))
            d.addErrback(catchError)
            d.addCallback(lambda m: f'Status of {msg}: {bytes2str(m)}') # generamos el string
            d.addCallback(lambda m: self.msg(user, m)) # mandamos el string


class IIRCClientFactory(Interface):
    '''
    @ivar nickname
    '''

    def getUser(user):
        '''
        Return a deferred returning a string.
        '''

    def buildProtocol(addr):
        '''
        Return a protocol.
        '''


@implementer(IIRCClientFactory)
class IRCClientFactoryFromService(protocol.ClientFactory):
    protocol = IRCReplyBot
    nickname = None

    def __init__(self, service):
        self.service = service

    def getUser(self, user):
        return self.service.getUser(user)

components.registerAdapter(
    IRCClientFactoryFromService, IFingerService, IIRCClientFactory
)


@implementer(resource.IResource)
class UserStatusTree(resource.Resource):
    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild(b'RPC2', UserStatusXR(self.service))

    def render_GET(self, request):
        d = self.service.getUsers()
        def formatUsers(users):
            l = [f'<li><a href="{user}">{user}</a></li>' for user in users]
            return '<ul>' + ''.join(l) + '</ul>'
        d.addCallback(lambda x: [bytes2str(u) for u in x])
        d.addCallback(formatUsers)
        d.addCallback(str2bytes)
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET

    def getChild(self, path, request):
        if path == b'':
            return UserStatusTree(self.service)
        else:
            return UserStatus(path, self.service)

components.registerAdapter(UserStatusTree, IFingerService, resource.IResource)

class UserStatus(resource.Resource):
    def __init__(self, user, service):
        resource.Resource.__init__(self)
        self.user = user
        self.service = service

    def render_GET(self, request):
        d = self.service.getUser(self.user)
        d.addCallback(bytes2str)
        d.addCallback(html.escape)
        d.addCallback(str2bytes)
        d.addCallback(lambda m: b'<h1>%s</h1>' % self.user + b'<p>%s</p>' % m)
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET

class UserStatusXR(xmlrpc.XMLRPC):
    def __init__(self, service):
        xmlrpc.XMLRPC.__init__(self)
        self.service = service

    def xmlrpc_getUser(self, user):
        return self.service.getUser(user)


@implementer(IFingerService, IFingerSetterService)
class MemoryFingerService(service.Service):
    def __init__(self, users):
        self.users = users

    def getUser(self, user):
        if isinstance(user, str):
            user = bytes2str(user)
        return defer.succeed(self.users.get(user, b'No such user'))

    def getUsers(self):
        return defer.succeed(list(self.users.keys()))

    def setUser(self, user, status):
        self.users[user] = status

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
f = MemoryFingerService({b'moshez': b'Happy and well'}) # volvemos a memoria

serviceCollection = service.IServiceCollection(application)
f.setServiceParent(serviceCollection)
# basicamnete explicado y sin animo de decir que así funciona
# components.registerAdapter(FingerFactoryFromService, IFingerService, IFingerFactory) [línea 107]
# más o menos quiere decir (de atrás para adelante)
# cuando llame a IFingerFactory con un argumento/objeto que implemente IFingerService
# traer adaptador FingerFactoryFromService
# la magia que quieren aplicar es que pueden marcar una clase para poder traer su adaptador
# o sea implementar POA y evitar duck typing o duck punching (supongo)
strports.service('tcp:79', IFingerFactory(f)).setServiceParent(serviceCollection)
strports.service('tcp:8000', server.Site(resource.IResource(f))).setServiceParent(serviceCollection)
i = IIRCClientFactory(f)
i.nickname = 'fingerbot'
internet.ClientService(
    endpoints.clientFromString(
        reactor, 'tcp:irc.freenode.org:6667' # needs registration, suggest to install own server
    ),
    i,
).setServiceParent(serviceCollection)
# se ve que no está ligado a la clase si no a la interfaz y por lo tanto no hay
# dependencia fuerte
strports.service('tcp:1079:interface=127.0.0.1', IFingerSetterFactory(f)).setServiceParent(serviceCollection)
