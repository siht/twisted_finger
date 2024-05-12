# como correr?
# python finger.py
from twisted.internet import (
    endpoints,
    protocol,
    reactor,
)
from twisted.protocols import basic


class FingerProtocol(basic.LineReceiver): # LineReceiver es un protocolo que ya tiene los métodos para recibir texto del cliente
    def lineReceived(self, user): # esta vez no estamos dropeando la conexion inmediatamente, ahora esperamos input del cliente
        self.transport.write(b'No such user\r\n') # hacemos una respuesta mock, nunca hay usuarios
        self.transport.loseConnection()


class FingerFactory(protocol.ServerFactory):
    protocol = FingerProtocol


def main():
    # qué hace esto? al abrir una consola y escribir `telnet localhost 1079`
    # escribes el nombre de un usuario y te regresa: No such user
    # un servicio finger util para trolear
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory())
    reactor.run()


if __name__ == '__main__':
    main()
