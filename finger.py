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
        self.transport.loseConnection() # y volvemos a hacer nada


class FingerFactory(protocol.ServerFactory):
    protocol = FingerProtocol


def main():
    # qué hace esto? al abrir una consola y escribir `telnet localhost 1079`
    # escribes algo pulsas enter y... te cierra la conexión
    # como mínimo el protocolo ahora te pide input, ahora falta que te regrese algo útil
    # como el usuario
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory())
    reactor.run()


if __name__ == '__main__':
    main()
