### python-packages
import time
import socket 
import json
import re
import subprocess

### local-packages
from timeout import timeout
from logger import *

class TrackSync():

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
                log.info(f"Keyboard Interrupt")
                self.close_socket()
            except BrokenPipeError:
                log.error(f"Broken Pipe")
                self.close_socket()
            except ConnectionResetError:
                log.error(f"Connection Reset")
                self.close_socket()
    
    def close_socket(self):
        """
            Close the socket connection 's'
        """
        if self.s != None:
            self.s.close()
        if self.conn != None:
            self.conn.close()
        log.info("Sockets Closed")

    def set_track(self):
        """
            Bind to Delphi Track sockets for communication
        """
        log.info("Searching for Delphi Track...")
        log.info(f"Hostname: {socket.gethostname()}")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.s:
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.bind((self.HOST, self.PORT))
            self.s.listen(1)
            self.conn, self.addr = self.s.accept()
            log.info("Found Delphi Track - Connection from: " + str(self.addr))

    def parse_message2(self, message):
        """
            The Delphi Track system send 3 messages during the syncing process.
            Message 2 contains the time and date information set on the track system.
            message: message 2 received from Delphi Track during syncing process
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
        message_parsed["dayofmonth"]    = message_int[9] 
        message_parsed["dayofweek"]     = message_int[11]
        message_parsed["month"]         = message_int[13] + 1 # range is 0-11 in java
        message_parsed["year"]          = year_int
    
        log.info("MESSAGE 2 PARSED: ", message_parsed)
    
        return message_parsed

    def sync_time(self):
        """
            Send 3 responses to Delphi Track
            Parse the receive message 2
            Set the date and time of local Zotac using message 2
        """
        self.send_response(response = '1006051003E8') # response 1
        self.send_response(response = '1006101003DD') # response 2
        self.send_response(response = '1006061003E7') # response 3

        try:
            message123 = ""
            message123 = self.receive_message()
        except Exception as e:
            log.exception(f"{e}")

        if len(message123) < 74:
            log.info("Aborting Sync")
            return

        message1 = message123[:24]
        message2 = message123[24:-12]
        message3 = message123[-12:]

        log.info(f"MESSAGE123 - {message1} {message2} {message3}")
        assert message123 == message1 + message2 + message3

        m2hash = self.parse_message2(message2)
        dt_date = f"{m2hash['year']}-{m2hash['month']:02d}-{m2hash['dayofmonth']:02d}"
        dt_time = f"{m2hash['hour']:02d}:{m2hash['minute']:02d}:{m2hash['second']:02d}"
        
        subprocess.check_call(['./set_datetime.sh', dt_date, dt_time])
        log.info(f"Set Date and Time: {dt_date} {dt_time}")

    def send_response(self, response):
        """
            Send a response to Delphi Track
        """
        to_send = bytes.fromhex(response)
        self.conn.sendall(to_send)
        log.info(f"SENT RESPONSE: {response}")

    @timeout(2)    
    def receive_message(self):
        """
            Receive a message from Delphi Track
        """
        log.info("WAITING FOR MESSAGE...")
        total = ""
        while True:
            data = self.conn.recv(1)
            total += data.hex()
            if not data and total != "":
                break

        log.info(f"MESSAGE: {total}")
        return total

if __name__ == "__main__":
    strack = TrackSync()
    strack.close_socket()
