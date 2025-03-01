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
from twisted.spread import pb
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
        self.putChild(b'', self)

    def _cb_render_GET(self, users, request): # demostrando que se pueden cargar plantillas
        userOutput = ''.join(
            [f'<li><a href="{bytes2str(user)}">{bytes2str(user)}</a></li>' for user in users]
        )
        response_output = str2bytes(
            '''
            <html><head><title>Users</title></head><body>
            <h1>Users</h1>
            <ul>
            %s
            </ul></body></html>'''
            % userOutput
        )
        request.write(response_output)
        request.finish()

    def render_GET(self, request):
        d = self.service.getUsers()
        d.addCallback(self._cb_render_GET, request)
        # signal that the rendering is not complete
        return server.NOT_DONE_YET

    def getChild(self, path, request):
        return UserStatus(user=path, service=self.service)

components.registerAdapter(UserStatusTree, IFingerService, resource.IResource)

class UserStatus(resource.Resource):
    def __init__(self, user, service):
        resource.Resource.__init__(self)
        self.user = user
        self.service = service

    def _cb_render_GET(self, status, request): # demostrando que se pueden cargar plantillas
        request.write(
            b'''<html><head><title>%s</title></head>
            <body><h1>%s</h1>
            <p>%s</p>
            </body></html>'''
            % (self.user, self.user, status)
        )
        request.finish()

    def render_GET(self, request):
        d = self.service.getUser(self.user)
        d.addCallback(self._cb_render_GET, request)
        # signal that the rendering is not complete
        return server.NOT_DONE_YET

class UserStatusXR(xmlrpc.XMLRPC):
    def __init__(self, service):
        xmlrpc.XMLRPC.__init__(self)
        self.service = service

    def xmlrpc_getUser(self, user):
        return self.service.getUser(user)


class IPerspectiveFinger(Interface):
    def remote_getUser(username):
        '''
        Return a user's status.
        '''

    def remote_getUsers():
        '''
        Return a user's status.
        '''


@implementer(IPerspectiveFinger)
class PerspectiveFingerFromService(pb.Root):
    def __init__(self, service):
        self.service = service

    def remote_getUser(self, username):
        return self.service.getUser(username)

    def remote_getUsers(self):
        return self.service.getUsers()

components.registerAdapter(
    PerspectiveFingerFromService, IFingerService, IPerspectiveFinger
)


@implementer(IFingerService)
class FingerService(service.Service): # de vuelta para desmostrar un punto
    def __init__(self, filename):
        print('si')
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
            user = str2bytes(user)
        return defer.succeed(self.users.get(user, b'No such user'))

    def getUsers(self):
        return defer.succeed(list(self.users.keys()))


def makeService(config):
    # finger on port 79
    s = service.MultiService()
    f = FingerService(config['file'])
    f.setServiceParent(s)

    h = strports.service('tcp:79', IFingerFactory(f))
    h.setServiceParent(s)
    # website on port 8000
    r = resource.IResource(f)
    r.templateDirectory = config['templates']
    site = server.Site(r)
    j = strports.service('tcp:8000', site)
    j.setServiceParent(s)
    # ssl on port 443
    if config.get('ssl'):
        k = strports.service('ssl:port=443:certKey=cert.pem:privateKey=key.pem', site)
        k.setServiceParent(s)
    # irc fingerbot
    if 'ircnick' in config:
        i = IIRCClientFactory(f)
        i.nickname = config['ircnick']
        ircserver = config['ircserver']
        b = internet.ClientService(
        endpoints.HostnameEndpoint(reactor, ircserver, 6667), i
        )
        b.setServiceParent(s)
    # Pespective Broker on port 8889
    if 'pbport' in config:
        m = internet.StreamServerEndpointService(
        endpoints.TCP4ServerEndpoint(reactor, int(config['pbport'])),
        pb.PBServerFactory(IPerspectiveFinger(f)),
        )
        m.setServiceParent(s)
    return s
