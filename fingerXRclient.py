from xmlrpc.client import Server

server = Server('http://127.0.0.1:8000/RPC2')
print(server.getUser('moshez'))
