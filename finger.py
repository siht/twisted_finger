# como correr?
# python finger.py
from twisted.internet import (
    endpoints,
    protocol,
    reactor,
)


class FingerProtocol(protocol.Protocol): # basicamente su trabajo es escuchar y enviar, y tener una lógica de protocolo no de negocio
    pass


class FingerFactory(protocol.ServerFactory): # su trabajo es ofrecer lógica de negocio y datos
    protocol = FingerProtocol


def main():
    # como funciona twisted Enpoint(Factory(Protocol))
    # resumiendo de manera sencilla necesitas un punto de acceso (Endpoint)
    # que escuche un factory que a su vez tenga un protocolo de comunicacion
    # qué hace esto? nada. el protocolo no hace algo y no hay datos, pero puedes
    # ir a una consola y escribir `telnet localhost 1079` y te dará un prompt que
    # hace nada
    fingerEndpoint = endpoints.serverFromString(reactor, 'tcp:1079')
    fingerEndpoint.listen(FingerFactory())
    reactor.run()


if __name__ == '__main__':
    main()
