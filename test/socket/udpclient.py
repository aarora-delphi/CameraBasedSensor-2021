import socket

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
#client.bind(("",5000))
client.bind(("0.0.0.0",5000))
print("Starting UDP Bind...")
while True:
    data, addr = client.recvfrom(1024)
    print(data)
