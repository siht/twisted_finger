# como correr?
# python finger.py
from twisted.internet import (
    defer,
    endpoints,
    protocol,
    reactor,
)
from twisted.protocols import basic


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
    protocol = FingerProtocol # cuando registramos el protocolo dentro del factory se crea una propiedad dentro del protocol para acceder

    def __init__(self, users):
        self.users = users

    def getUser(self, user):
        return defer.succeed(self.users.get(user, b'No such user')) # defer.succeed hace lo bloqueanto como no bloqueante y regresa un defer


def main():
    # qué hace esto? al abrir una consola y escribir `telnet localhost 1079`
    # escribes el nombre de un usuario moshez regresa: Happy and well
    # cualquier otro nombre te regresa: No such user
    # ahora ya hay una fuente de datos intercambiable y tenemos nuestra primera db (un diccionario)
    # ahora ya empieza parecerse a finger
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory({b'moshez': b'Happy and well'}))
    reactor.run()


if __name__ == '__main__':
    main()
