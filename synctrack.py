#!/usr/bin/env python3

### python-packages
import time
import socket 
import json
import re
import subprocess
import select
import multiprocessing
import queue
import signal
from collections import deque

### local-packages
from timeout import timeout, TimeoutError
from logger import *
from runtrack import DConnect
import pickle_util

should_run = True # global variable

class TrackSync():

    def __init__(self, name = "Track1", connect = (None, None, None)):
        self.name = name
        self.set_connect(connect)
        self.startTime = time.monotonic()
        self.errorTime = None
        self.resend_message = False
        self.last_vehicle_message = None
        
        self.offset = int(subprocess.check_output("./script/get_timezone.sh").strip()) # gets tz diff in seconds from utc
        self.buffer_file = f"storage-oak/event_buffer.pb"
        self.event_buffer = pickle_util.load(self.buffer_file, error_return = deque(maxlen=2000)) # store last 2K events
    
    def set_connect(self, connect):
        self.connect = connect != (None, None, None)
        self.s, self.conn, self.addr = connect
        self.message_conn = [self.conn]

    def errorbeat(self, second_interval = 240):
        """
            Used as a failsafe to exit synctrack
            Returns True if second_interval has passed since error
        """
        currentTime = time.monotonic()
        
        # first time method is called
        if self.errorTime == None:
            self.errorTime = currentTime 
            log.info(f"Setting self.errorTime to {currentTime}")
            return False
        
        # if method has not been called in a while - set self.errorTime
        elif currentTime - self.errorTime > second_interval * 1.5:
            log.info(f"Resetting self.errorTime to {currentTime}")
            self.errorTime = currentTime
            return False
        
        # if method is actively being used, this action will occur
        elif currentTime - self.errorTime > second_interval:
            log.info("Condition met for self.errorTime")
            return True
                
        return False

    def heartbeat(self, second_interval = 240):
        """
            Sends heartbeat every 4 minutes
        """
        currentTime = time.monotonic()
        if currentTime - self.startTime > second_interval:        
            self.startTime = currentTime
            self.conn = self.message_conn_head()
            self.send_response(response = '000000000000000000000', encode_type = 'str') # incorrect - see spec (do in runtrack)

    def sync_on_heartbeat(self):
        """
            Command to Sync with Insight Track with heartBeat during Regular Interval
        """
        return self.sync_wrapper(self.heartbeat)

    def sync_on_boot(self):
        """
            Command to Sync with Insight Track on Track Boot
        """
        log.info(f"Performing Boot Sync")
        return self.sync_wrapper(self.sync_time)

    def sync_on_recv(self):
        """
            Command to Sync with Insight Track during Regular Operation
        """
        print(f"[INFO] sync")
        return self.sync_wrapper(self.sync_listen) 

    def sync_listen(self):
        """
            Respond to Messages Received from Insight Track
        """

        try:
            self.receive_message(timeout_sec = 1, decode_type = 'str')
        except TimeoutError:
            pass
            
        if self.message == "": 
            return
        
        self.evaluate_message(self.message)
        
        
    def evaluate_message(self, message):
        """
            Given a message, evaluate response to send
        """       
        message = message.rstrip() # remove newline / tab char
                
        log.info(f"TRACK MESSAGE RECEIVED: {message}")
        
        if message == '{"get":"serialnumber"}':
            self.send_response(response='{"serialnumber":"GXXXX301XXXXX"}', encode_type = 'str') 

        elif message == '{"get":"partnumber"}':
            self.send_response(response='{"partnumber":"2500-TIU-2000"}', encode_type = 'str')

        elif message == '{"get":"firmwarepartno"}':
            self.send_response(response='{"firmwarepartno":"xxxxxx"}', encode_type = 'str')
        
        elif 'client' in message:
            self.send_response(response='hello', encode_type = 'str')      
        
        elif len(message) == 11 and message[:6] == 'Event|' and self.event_buffer:
            start_event = message[6:]
            current_event = self.event_buffer[-1].decode()[-6:-1]

            self.send_response(response=f'254000{self.timestamp()}00000', encode_type = 'str') # start message cycle
                
            for int_event in range(int(start_event),int(current_event)+1): # loop to send requested to current events
                str_event = str(int_event).zfill(5) 
                buffer_event = self.retrieve_event_from_buffer(str_event)
                if buffer_event:
                    self.send_response(response=buffer_event, encode_type = 'byte')
            
            self.send_response(response=f'255000{self.timestamp()}00000', encode_type = 'str') # end message cycle   
                    
        
        # boot sync
        elif message == '1001053030303030301003c8':
            self.send_response(response = '1006051003E8') # response 1

        elif len(message) == 40 and message[:6] == '100110':
            self.send_response(response = '1006101003DD') # response 2
            self.apply_sync_datetime(message)

        elif message == '1001061003e7':
            self.send_response(response = '1006061003E7') # response 3
            
    def timestamp(self):
        """
            Returns the epoch timestamp with offset applied
        """
        return int(time.time()) + self.offset
    
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
        
        self.apply_sync_datetime(message2)

    def apply_sync_datetime(self, message2):
        """
           Apply the datetime received from Delphi Track to sync clocks 
        """
        m2hash = self.parse_message2(message2)
        dt_date = f"{m2hash['year']}-{m2hash['month']:02d}-{m2hash['dayofmonth']:02d}"
        dt_time = f"{m2hash['hour']:02d}:{m2hash['minute']:02d}:{m2hash['second']:02d}"
        
        subprocess.check_call(['./script/set_datetime.sh', dt_date, dt_time])
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
    
        log.info(f"MESSAGE 2 PARSED: {message_parsed}")
    
        return message_parsed

    def send_response(self, response, encode_type = 'hex'):
        """
            Send a Response to Insight Track
        """
        if encode_type == 'hex':
            to_send = bytes.fromhex(response)
        elif encode_type == 'str':
            to_send = bytes(response+'\n', encoding='utf-8')
        elif encode_type == 'byte':
            to_send = response
        
        self.conn.sendall(to_send)
        log.info(f"SENT RESPONSE: {response} - Encoded as {to_send}")

    
    def retrieve_event_from_buffer(self, event):
        """
            Retrieves event from buffer
        """
        event_buffer_list = list(self.event_buffer)
        index = search(event_buffer_list, 0, len(event_buffer_list) - 1, event)
        
        if index != -1:
            requested_event = event_buffer_list[index]
            log.info(f"Found Requested Event {event}: {requested_event}")
            return requested_event
        else:
            log.info(f"Did Not Find Requested Event {event}")
            return None
    
    def add_event_to_buffer(self, event):
        """
            Saves event to self.event_buffer + to disk on interval
        """
        self.event_buffer.append(event)

        if int(event[-5:]) % 100 == 0:
            self.save_event_buffer()
    
    def save_event_buffer(self):
        """
            Saves Event Buffer to Disk
        """
        log.info(f"Saving Event Buffer to Disk")
        pickle_util.save(self.buffer_file, self.event_buffer)  

    def send_vehicle_message(self, message):
        """
            Send a vehicle message to Insight Track
        """
        self.add_event_to_buffer(message)
        
        conn = self.message_conn_head()
        
        if self.resend_message and self.last_vehicle_message != None:
            self.resend_message = False
            conn.sendall(self.last_vehicle_message)
            log.info(f"RESENT VEH MESSAGE: {self.last_vehicle_message}")
            
        self.last_vehicle_message = message
        conn.sendall(message)
        print(f"SENT VEH MESSAGE: {message}")

    def close_message_conn(self, conn):
        """
            Close message connection if matching conn
        """
        if conn in self.message_conn:
            self.message_conn.remove(conn)
            log.info(f"Removed from self.message_conn: {conn}")
            log.warning(f"self.message_conn is Empty - Length {len(self.message_conn)}")
    
    def append_message_conn(self, conn):
        """
            Append message connection in self.message_conn
        """
        if conn not in self.message_conn:
            self.message_conn.append(conn)
            log.info(f"Added to self.message_conn: {conn}")
            log.info(f"Size of self.message_conn: {len(self.message_conn)}")
            log.info(f"Head of self.message_conn: {self.message_conn_head()}")

    def message_conn_head(self):
        """
            return first item in self.message_conn
        """
        return self.message_conn[0]

    def decode_message(self, data):
        """
            Returns decoded data
        """
        print(f"RECEIVED DATA - {data}")
        try:
            message = data.decode()
        except UnicodeDecodeError:
            message = data.hex()
        
        return message

    def receive_message(self, timeout_sec = 2, decode_type = 'hex'):
        """
            Catch method to apply timeout decorator to self.receive_message_operation
        """
        return timeout(timeout_sec)(self.receive_message_operation)(decode_type) # timeout decorator applied
	
    def receive_message_operation(self, decode_type):
        """
            Receive a Message from Insight Track
        """
        self.message = ""
        while True:
            data = self.conn.recv(1)
            
            if decode_type == 'hex':
                self.message += data.hex()
            elif decode_type == 'str':
                self.message += data.decode()
                
                if data.decode() == '}':
                    log.info("Found '}' Brace in recv")
                    break
            
            if not data and self.message != "":
                break

        return self.message    

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
        except socket.timeout:
            log.info(f"Socket Timer Expired")
            return 4
        except Exception as e:
            log.error(f"New Exception: {e}")
            return -1
        
        return 0


def search(arr, l, h, key):
    """
        Performs Binary Search with Pivot for key (event) in arr (event_buffer)
        Returns -1 if key not present, otherwise returns index
    """
    def access_arr(index):
        return arr[index].decode()[-6:-1] # extract event number from event - last 5 characters before newline
    
    if l > h:
        return -1
     
    mid = (l + h) // 2
    if access_arr(mid) == key:
        return mid
 
    # If arr[l...mid] is sorted
    if access_arr(l) <= access_arr(mid):
 
        # As this subarray is sorted, we can quickly
        # check if key lies in half or other half
        if key >= access_arr(l) and key <= access_arr(mid):
            return search(arr, l, mid-1, key)
        return search(arr, mid + 1, h, key)
 
    # If arr[l..mid] is not sorted, then arr[mid... r]
    # must be sorted
    if key >= access_arr(mid) and key <= access_arr(h):
        return search(arr, mid + 1, h, key)
    return search(arr, l, mid-1, key)

def restart_connect(dconn, strack, read_list):
    """
        Shorthand to reconnect to Track + Close All Connections
    """
    log.info(f"Closing All Connections")
    for conn in read_list:
        conn.close()
                
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
        # restart_connect(dconn, strack)
        return False
    
    return True

def signal_handler(sig, frame):
    """
        Sets should_run to False when Keyboard Interrupt is Caught Ending synctrackmain loop
    """
    global should_run
    log.info('synctrack Signal Handler Caught - setting should_run to False')
    should_run = False

def synctrackmain(work_queue, boot = True):
    """
        Main Loop to recv and send messages to Insight Track
    """
    global should_run
    signal.signal(signal.SIGINT, signal_handler)
    
    dconn = DConnect(connect = True)
    strack = TrackSync(connect = dconn.get_conn())            
    
    log.info("Starting Sync Event Loop")
    read_list = [dconn.s, dconn.conn]
    
    while should_run:
    
        readable, writable, errored = select.select(read_list, [], [], 0) # non-blocking
        
        # -------------------------------------------------
        
        for s in readable:
            if s is dconn.s:
                client_socket, address = dconn.accept_conn()
                read_list.append(client_socket)
            else:
                try:
                    
                    data = s.recv(1024)
                    
                    if data:
                        strack.conn = s # set connection to use
                        message = strack.decode_message(data)                        
                        strack.evaluate_message(message)
                    
                    elif s == dconn.conn: # keep original connection from closing when no data present
                        pass
                    
                    else:
                        log.info(f"NO CONN DATA - CLOSING {s}")
                        strack.close_message_conn(s)
                        s.close()
                        read_list.remove(s)   
                
                except (BrokenPipeError, ConnectionResetError) as e:
                    log.error(f"{e} - ON DATA READ/REPLY - CLOSING {s}")
                    strack.close_message_conn(s)
                    s.close()
                    read_list.remove(s)
                    strack.resend_message = True
        
        # -------------------------------------------------
        
        try:
            if strack.message_conn:
                vehicle_message = None
                ### strack.heartbeat() # TO DO - Put method in runtrack.py
                vehicle_message = work_queue.get(block=False)
                strack.send_vehicle_message(vehicle_message) 
            else:
                log.warning("NO MESSAGE CONN - Restarting All Connections")
                strack.save_event_buffer()
                restart_connect(dconn, strack, read_list)
                read_list = [dconn.s, dconn.conn]     
        
        except queue.Empty: 
            pass
            
        except (BrokenPipeError, ConnectionResetError) as e:
            log.error(f"{e} when Sending Vehicle Message / Heartbeat - Closing Head of self.message_conn")
            strack.close_message_conn(strack.message_conn_head())
            if vehicle_message:
                strack.resend_message = True
        

    strack.save_event_buffer()
    dconn.close_socket()
    log.info(f"synctrack Process Exited")

if __name__ == "__main__":
    work_queue = multiprocessing.Queue()
    synctrackmain(work_queue, boot = True)
