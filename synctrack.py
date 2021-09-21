#!/usr/bin/env python3

### python-packages
import time
import socket 
import json
import re
import subprocess

### local-packages
from timeout import timeout, TimeoutError
from logger import *
from runtrack import DConnect

class TrackSync():

    def __init__(self, name = "Track1", connect = (None, None, None)):
        self.name = name
        self.set_connect(connect)
    
    def set_connect(self, connect):
        self.connect = connect != (None, None, None)
        self.s, self.conn, self.addr = connect
    
    def sync_on_boot(self):
        """
            Command to Sync with Track System on Track Boot
        """
        log.info(f"Performing Boot Sync")
        return self.sync_wrapper(self.sync_time)

    def sync_on_recv(self):
        """
            Listen for hourly Sync Messages
        """
        log.info(f"Performing Sync Check")
        return self.sync_wrapper(self.sync_listen) 

    def sync_listen(self):
        """
            Parse messages received hourly
        """
        message = self.receive_message_blocking()
        if message != "":
            log.info(f"TRACK SYNC MESSAGE RECEIVED: {message}")
            # TO DO - Translate Messages and act upon them  

    def sync_time(self):
        """
            Send 3 responses to Delphi Track
            Parse the receive message 2
            Set the date and time of local Zotac using message 2
        """
        self.send_response(response = '1006051003E8') # response 1
        self.send_response(response = '1006101003DD') # response 2
        self.send_response(response = '1006061003E7') # response 3

        message123 = self.receive_message()
        log.info(f"MESSAGE: {message123}")

        if len(message123) < 74:
            log.info("Aborting Boot Sync")
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

    def send_response(self, response):
        """
            Send a response to Delphi Track
        """
        to_send = bytes.fromhex(response)
        self.conn.sendall(to_send)
        log.info(f"SENT RESPONSE: {response}")
 
    @timeout(2)
    def receive_message(self):
        return self.receive_message_operation() # timeout applied

    def receive_message_blocking(self): 
        return self.receive_message_operation() # blocking applied

    def receive_message_operation(self):
        """
            Receive a message from Delphi Track
        """
        total = ""
        while True:
            data = self.conn.recv(1)
            total += data.hex()
            if not data and total != "":
                break

        return total        

    def sync_wrapper(self, func):
        """
            Try Except Wrapper to handle socket status on func
            Status Code is returned
        """
        try:
            func()
        except KeyboardInterrupt:
            log.info(f"Keyboard Interrupt")
            return 1
        except BrokenPipeError:
            log.error(f"Broken Pipe")
            return 2
        except ConnectionResetError:
            log.error(f"Connection Reset")
            return 3
        except TimeoutError:
            log.info(f"Timer Expired")
            return 4
        except:
            log.error(f"New Exception")
            return -1
        
        return 0

def restart_connect(dconn, strack):
    """
        Shorthand to reconnect to Track
    """
    log.info(f"Restarting Track Connection")
    dconn.close_socket()
    dconn.set_track()
    strack.set_connect(dconn.get_conn())

def mend_status(status, dconn, strack):
    """
        Parse Status and return if script should continue
    """
    if status == 1 or status == -1:
        return False
    if status == 2 or status == 3:
        restart_connect(dconn, strack)
    
    return True

if __name__ == "__main__":
    dconn = DConnect(connect = True)
    strack = TrackSync(connect = dconn.get_conn())
    status = strack.sync_on_boot()
    mend_status(status, dconn, strack)
    
    while True:
        status = strack.sync_on_recv()
        if not mend_status(status, dconn, strack):
            break
            
    dconn.close_socket()
        
    
    
