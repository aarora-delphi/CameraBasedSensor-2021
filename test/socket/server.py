import socket
import sys
import json


jsonResult = {"first":"You're", "second":"Awsome!"}
jsonResult = json.dumps(jsonResult)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print(f'Socket error because of {err}')

port = 5000
address = "0.0.0.0"

try:
    #sock.connect(('localhost', port))
    #sock.send(jsonResult.encode())
    sock.bind((address, port))
    sock.listen(1)
    conn, addr = sock.accept()
    conn.send(jsonResult.encode())
except socket.gaierror:

    print('There an error resolving the host')

    sys.exit() 
        
print(jsonResult, 'was sent!')
sock.close()
