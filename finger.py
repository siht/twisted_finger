# como correr?
# python finger.py
from twisted.internet import (
    endpoints,
    protocol,
    reactor,
)
from twisted.protocols import basic


class FingerProtocol(basic.LineReceiver):
    def lineReceived(self, user): # ahora nuestra fuente de los datos es el factory
        self.transport.write(self.factory.getUser(user) + b'\r\n')
        self.transport.loseConnection()


class FingerFactory(protocol.ServerFactory):
    protocol = FingerProtocol # cuando registramos el protocolo dentro del factory se crea una propiedad dentro del protocol para acceder

    def __init__(self, users):
        self.users = users

    def getUser(self, user):
        return self.users.get(user, b'No such user')


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
