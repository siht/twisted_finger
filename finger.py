# como correr?
# python finger.py
from twisted.internet import (
    endpoints,
    protocol,
    reactor,
)


class FingerProtocol(protocol.Protocol): # ofrecemos la primera lógica. al recibir la conexión se la cerramos
    def connectionMade(self):
        self.transport.loseConnection()


class FingerFactory(protocol.ServerFactory):
    protocol = FingerProtocol


def main():
    # qué hace esto? al abrir una consola y escribir `telnet localhost 1079` te cierra la conexión
    # eso lo hace la lógica del protocolo
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory())
    reactor.run()


if __name__ == '__main__':
    main()
