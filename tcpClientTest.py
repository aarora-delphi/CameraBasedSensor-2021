import time
import socket 
import json
import re

class DTrack():

    def __init__(self, name = "Track1", connect = True):
        self.name = name
        
        # connect to track system or not
        self.connect = connect
        
        self.HOST = "0.0.0.0"
        self.PORT = 5000
        self.s = None
        self.conn = None
        self.addr = None
        
        # set Track connection up
        if self.connect:
            try:
                self.set_track()
                self.sync_time()
            except KeyboardInterrupt:
                print(f"[INFO] Keyboard Interrupt")
                self.close_socket()
            except BrokenPipeError:
                print(f"[INFO] Broken Pipe")
                self.close_socket()
            except ConnectionResetError:
                print(f"[INFO] Connection Reset")
                self.close_socket()
    
    def close_socket(self):
        if self.s != None:
            self.s.close()
        if self.conn != None:
            self.conn.close()
        print("[INFO] Sockets Closed")

    def set_track(self):
        print("[INFO] Searching for Delphi Track...")
        print(f"[INFO] Hostname: {socket.gethostname()}")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.s:
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.bind((self.HOST, self.PORT))
            self.s.listen(1)
            self.conn, self.addr = self.s.accept()
            print("[INFO] Found Delphi Track - Connection from: " + str(self.addr))

    def parse_message2(self, message):
        """
        The Delphi Track system send 3 messages during the syncing process.
        Message 2 contains the time and date information set on the track system.
        """
        message_pair = re.findall('..?', message)
        message_bytes = []
        message_int = []
        message_parsed = {} # dictionary
    
        for pair in message_pair:
            byte_val = bytes.fromhex(pair)
            int_val = int.from_bytes(byte_val, "little", signed="True")
    
            message_bytes.append(byte_val)
            message_int.append(int_val)
    
        year_int = int.from_bytes(message_bytes[15] + message_bytes[16], "little", signed="True")
    
        message_parsed["second"]        = message_int[3]
        message_parsed["minute"]        = message_int[5]
        message_parsed["hour"]          = message_int[7]
        message_parsed["dayofmonth"]    = message_int[9] # maybe add 1 here bc dtrack subtracts 1
        message_parsed["dayofweek"]     = message_int[11]
        message_parsed["month"]         = message_int[13]
        message_parsed["year"]          = year_int
    
        print("MESSAGE 2 PARSED: ", message_parsed)
    
        return message_parsed

    def sync_time(self):
        self.send_response(response = '1006051003E8') # response 1
        self.send_response(response = '1006101003DD') # response 2
        self.send_response(response = '1006061003E7') # response 3
       
        message123 = self.receive_message()
        message1 = message123[:24]
        message2 = message123[24:-12]
        message3 = message123[-12:]
        
        print("MESSAGE123", message1, message2, message3)
        assert message123 == message1 + message2 + message3

        m2hash = self.parse_message2(message2)

        #message1 = self.receive_message()             # message 1
        #self.send_response(response = '1006051003E8') # response 1

        #message2 = self.receive_message()             # message 2
        #self.send_response(response = '1006101003DD') # response 2
        
        #message3 = self.receive_message()             # message 3
        #self.send_response(response = '1006061003E7') # response 3

    def send_response(self, response):
        to_send = bytes.fromhex(response)
        self.conn.sendall(to_send)
        print(f"SENT RESPONSE: {response}")

    def receive_message(self):
        print("RECEIVING MESSAGE...")
        total = ""
        while True:
            data = self.conn.recv(1)
            total += data.hex()
            if not data and total != "":
                break

        print(f"MESSAGE: {total}")
        return total

if __name__ == "__main__":
    dtrack = DTrack()
    dtrack.close_socket()
