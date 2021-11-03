### python-packages
import time
import socket 
import json
from collections import deque
import pickle
from datetime import datetime, timezone
import subprocess

### local-packages
import pickle_util
from logger import *

class DConnect():
    def __init__(self, connect = True):
        self.connect = connect
        self.HOST = "0.0.0.0"
        self.PORT = 5000
        
        self.s = None
        self.conn = None
        self.addr = None
        
        if self.connect:
            self.set_track()
    
    def set_track(self):
        """
            Bind to Delphi Track sockets for communication
        """
        log.info("Searching for Delphi Track...")
        log.info(f"Hostname: {socket.gethostname()}")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ### self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) # allows multiple listen to same port
        self.s.bind((self.HOST, self.PORT))
        self.s.listen(2)
        self.conn, self.addr = self.accept_conn()
    
    def accept_conn(self):
        """
            Accept connection
        """
        conn, addr = self.s.accept()
        log.info(f"Found Connection from: {addr} - {conn}")
        return conn, addr
    
    def get_conn(self):
        """
            Return the Delphi Track Sockets
        """
        return (self.s, self.conn, self.addr)
    
    def close_socket(self):
        """
            Close the socket 's'
        """
        if self.s != None:
            self.s.close()
        if self.conn != None:
            self.conn.close()
        log.info("Sockets Closed")
    

class DTrack():

    def __init__(self, name = '001', connect = False): # connect = (None, None, None)):
        self.name = name
        self.set_connect(connect)
        
        self.offset = int(subprocess.check_output("./script/get_timezone.sh").strip()) # gets tz diff in seconds from utc
        self.buffer_file = f"storage-oak/buffer_position.pb"
        ###self.heartbeat_timer = time.monotonic()
        
        # JSON Logging related variables
        self.min_frames = 5
        self.car_counts = deque([-1]*self.min_frames)
        self.in_lane = False
        self.out_lane = True

    def get_buffer_position(self):
        """
            Loads, Increments, Saves, and Returns buffer_position
        """
        buffer_position = pickle_util.load(self.buffer_file, error_return = -1) + 1
        
        if buffer_position > 65535:
            buffer_position = 0
        
        pickle_util.save(self.buffer_file, buffer_position)
        return buffer_position

    def set_name(self, name):
        """
            Sets self.name defined as the station number 000 - 008
        """
        self.name = name
    
    def set_connect(self, connect):
        """
            Prevents message sending for invalid self.name station number
        """
        if self.name == '000' or self.name == '255': # set to not connect
            connect = False
            log.info(f'Track Messaging Disabled for Station {self.name}')
        
        self.connect = connect # determines if messages are sent

    def __create_track_string(self, json_msg):
        """
            Creates bit string for Delphi Track system
        """
        loop_num = self.name 
        status = ''
        timestamp = str(int(json_msg['timestamp']))
        vehicle_id = str(json_msg['vehicle_id']).zfill(5)
        
        if json_msg['status']  == '001':
            status = '255'
        elif json_msg['status'] == '002':
            status = '000' 
        
        to_send = bytes(loop_num+status+timestamp+vehicle_id+'\n', 'utf-8')
        return to_send

    def log_car_detection(self, numCars):
        """
            Method sends json messages whenever a car is detected and enough frames have passed
            User can determine how many frames should pass before a message is sent by modifying
            the variable min_frames above
            Parameters:
            numCars: the number of cars detected in the frame by the model
        """
        
        json_message = {
                "camera_id": self.name,
                "timestamp": self.timestamp(),
                "vehicle_id": 0,
                "status": "000"
        }

        if numCars is None or self.min_frames < 1:
            print(json_message)
            return


        self.car_counts.append(numCars)
        self.car_counts.popleft()

        if self.car_counts == (deque([0]*self.min_frames)) and self.in_lane:
            json_message["status"] = "002" # Car left ROI
            self.out_lane = True
            self.in_lane = False

        elif self.car_counts == (deque([1]*self.min_frames)) and self.out_lane:
            json_message["status"] = "001" # Car entered ROI
            self.in_lane = True
            self.out_lane = False


        if json_message["status"] != "000":
            if self.connect:
                json_message["vehicle_id"] = self.get_buffer_position()
                ###self.heartbeat_timer = time.monotonic() # reset timer
            
            print(json_message)
            
            if self.connect:
                to_send = self.__create_track_string(json_message)
                return to_send
        
        ###else:
        ###    if self.connect:
        ###        return self.heartbeat()

    def timestamp(self):
        """
            return timestamp which is epoch time + timezone difference in seconds
        """
        ts = int(time.time()) + self.offset
        return ts

    ###def heartbeat(self, second_interval = 300):
    ###    """
    ###        Sends heartbeat every 5 minutes of inactivity
    ###    """
    ###    current_time = time.monotonic()
    ###    if current_time - self.heartbeat_timer > second_interval:
    ###        self.heartbeat_timer = current_time
    ###        to_send = bytes(f'000000{self.timestamp()}00000'+'\n', 'utf-8')
    ###        print(f"Heartbeat: {to_send}")
    ###        return to_send

