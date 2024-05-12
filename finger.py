# como correr?
# python finger.py
from twisted.internet import (
    endpoints,
    protocol,
    reactor,
)
from twisted.protocols import basic
from twisted.web import client


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
        return client.getPage(self.prefix + user) # recuerda el tutorial es antiguo y esto no funciona

# se supone client.getPage sirve para traer datos de internet de forma asíncrona
# además no podemos utilizar cualquier herramienta que no sea compatible con el
# reactor o el event manager, la tristeza nos invade

def main():
    # qué hace esto? al abrir una consola y escribir `telnet localhost 1079`
    # escribes el nombre de un usuario moshez regresa: el contenido de una web
    # ahora ya hay una fuente de datos intercambiable que seguimos cambiando
    # en este caso es una url y vamos a traer la info desde la red, recuerda
    # si esto no fuera asíncrono porbablemente se tardaría la ejecución
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory(prefix=b'http://livejournal.com/~'))
    reactor.run()


if __name__ == '__main__':
    main()
