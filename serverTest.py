import socket 

HOST = '172.16.15.60'
PORT = 2000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST,PORT))
    
print('trying a connection')
while True:
    data, addr = s.recvfrom(1024)
    print(data.decode("utf-8"))
    s.sendto(data.encode('utf-8'), addr)
    if not data:
        print("no more data")
        break
