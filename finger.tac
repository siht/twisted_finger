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
    service,
    strports,
)
from twisted.internet import (
    defer,
    protocol,
    reactor,
)
from twisted.protocols import basic
from twisted.web import (
    resource,
    server,
    static,
)


class FingerProtocol(basic.LineReceiver): # a partir de ahora este protocolo es asíncrono
    def lineReceived(self, user): # vamos a usar asincronicidad y el get user nos regresará un objeto Defer
        d = self.factory.getUser(user)

        def onError(err): # al cual le vamos a agregar callbacks (este es un error callback)
            return b'Internal error in server'
        d.addErrback(onError)

        def writeResponse(message): # este callback es cuando la información llegue correctamente
            self.transport.write(message + b'\r\n') # le regresamos al cliente la respuesta
            self.transport.loseConnection()
        d.addCallback(writeResponse)


class FingerResource(resource.Resource):
    def __init__(self, users):
        self.users = users
        resource.Resource.__init__(self)
        # we treat the path as the username

    def getChild(self, username, request):
        '''
        'username' is L{bytes}.
        'request' is a 'twisted.web.server.Request'.
        '''
        messagevalue = self.users.get(username)
        if messagevalue:
            messagevalue = messagevalue.decode('ascii')
        if username:
            username = username.decode('ascii')
        username = html.escape(username)
        if messagevalue is not None:
            messagevalue = html.escape(messagevalue)
            text = f'<h1>{username}</h1><p>{messagevalue}</p>'
        else:
            text = f'<h1>{username}</h1><p>No such user</p>'
        text = text.encode('ascii')
        return static.Data(text, 'text/html')


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
        return defer.succeed(self.users.get(user, b'No such user'))

    def getFingerFactory(self):
        f = protocol.ServerFactory()
        f.protocol = FingerProtocol
        f.getUser = self.getUser
        return f

    def getResource(self):
        r = FingerResource(self.users)
        return r

# asegurate de correr como root este script antes de correr telnet

# telnet localhost 79
# mohsez(o el usuario que esté en tu archivo) [enter]
# web browser -> localhost:8000/user

application = service.Application('finger', uid=1, gid=1) # como root
f = FingerService('/etc/users') # pon acá el nombre de un archivo x con -> usuario:mensaje

serviceCollection = service.IServiceCollection(application)
f.setServiceParent(serviceCollection)

strports.service('tcp:79', f.getFingerFactory()).setServiceParent(serviceCollection)
strports.service('tcp:8000', server.Site(f.getResource())).setServiceParent(serviceCollection)
