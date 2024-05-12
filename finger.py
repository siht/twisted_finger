# como correr?
# python finger.py
from twisted.internet import reactor


def main():
    # para que twisted o cualquier cosa que funcione asincronamente debe haber
    # un "event manager" o un "reactor" digamos que es un while que maneja eventos
    # que hace esto? nada, no hay lógica, sólo estamos poniendo la estructura
    reactor.run()


if __name__ == '__main__':
    main()
