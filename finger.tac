# como correr?
# python finger.py
from twisted.internet import (
    endpoints,
    protocol,
    reactor,
)
from twisted.internet.defer import Deferred
from twisted.protocols import basic
from twisted.web.client import (
    Agent,
    Headers,
)


class WebPageDataGetterProtocol(protocol.Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.remaining = 1024 * 10
        self.buffer = b''

    def dataReceived(self, bytes):
        if self.remaining:
            display = bytes[:self.remaining]
            self.buffer += display
            self.remaining -= len(display)

    def connectionLost(self, reason):
        self.finished.callback(self.buffer)


def getPage(url): # hacemos nuestro propio getPage asíncrono con las herramientas de twisted
    agent = Agent(reactor)
    d = agent.request(
        b'GET',
        url,
        Headers({'User-Agent': ['Twisted Web Client Example']}),
        None
    )

    def get_content(response):
        finished = Deferred()
        response.deliverBody(WebPageDataGetterProtocol(finished))
        return finished
    d.addCallback(get_content)

    return d


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


class FingerFactory(protocol.ServerFactory):
    protocol = FingerProtocol

    def __init__(self, prefix):
        self.prefix = prefix

    def getUser(self, user):
        return getPage(self.prefix % user)


def main():
    # qué hace esto? al abrir una consola y escribir `telnet localhost 1079`
    # escribes el nombre de un usuario moshez regresa: el contenido de una web
    # ahora ya hay una fuente de datos intercambiable que seguimos cambiando
    # en este caso es una url y vamos a traer la info desde la red, recuerda
    # si esto no fuera asíncrono porbablemente se tardaría la ejecución
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory(prefix=b'https://%s.livejournal.com/'))
    reactor.run()


if __name__ == '__main__':
    main()
