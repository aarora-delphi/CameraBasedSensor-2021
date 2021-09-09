### python-packages
import time
import socket 
import json
from collections import deque
import pickle
from datetime import datetime, timezone
import pytz
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
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((self.HOST, self.PORT))
        self.s.listen(1)
        self.conn, self.addr = self.s.accept()
        log.info("Found Delphi Track - Connection from: " + str(self.addr))
    
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

    def __init__(self, name = '001', connect = (None, None, None)):
        self.name = name
        self.resend_message = None
        self.set_connect(connect)
        
        self.offset = int(subprocess.check_output("./get_timezone.sh").strip()) # gets tz diff in seconds from utc
        self.buffer_file = f"storage-oak/buffer_position.pb"
        
        # JSON Logging related variables
        self.min_frames = 5
        ###self.pickle_car_count = f"storage-oak/car_count_{self.name}.pb"
        ###self.car_count = pickle_util.load(self.pickle_car_count, error_return = 0)
        self.car_counts = deque([-1]*self.min_frames)
        self.in_lane = False
        self.out_lane = True
        self.total_cars_count = 0
        self.first = 0
        self.prev = 0

    def get_buffer_position(self):
        buffer_position = pickle_util.load(self.buffer_file, error_return = 0) + 1
        if buffer_position > 99999:
            buffer_position = 1
        pickle_util.save(self.buffer_file, buffer_position)
        return buffer_position

    def set_name(self, name):
        self.name = name
    
    def set_connect(self, connect):
        # set to not connect
        if self.name == '000' or self.name == '255':
            connect = (None, None, None)
            log.info(f'Track Messaging Disabled for Station {self.name}')
        
        # connect to track system or not
        self.connect = connect != (None, None, None)
        self.s = connect[0]
        self.conn = connect[1]
        self.addr = connect[2]
        
        # resend saved message from past failed attempt
        if self.connect and self.resend_message != None:
            self.__send_json_message(self.resend_message)
            log.info(f'Resent Saved Message at Station {self.name}')
            self.resend_message = None

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
        s1 = int(time.time()) + self.offset # epoch time + timezone difference in seconds 

        json_message = {
                "camera_id": self.name,
                "timestamp":s1,
                "vehicle_id": 0, ###self.car_count+1,
                "status": "000"
        }

        if numCars is None or self.min_frames < 1:
            print(json_message)
            return

        self.car_counts.append(numCars)
        self.car_counts.popleft()

        if self.car_counts == (deque([0]*self.min_frames)) and self.in_lane:
            #Car left ROI
            json_message["status"] = "002"
            
            ###self.car_count += 1
            ###if self.car_count >= 99999:
            ###    self.car_count = 0
            ###pickle_util.save(self.pickle_car_count, self.car_count)
            
            self.out_lane = True
            self.in_lane = False

        elif self.car_counts == (deque([1]*self.min_frames)) and self.out_lane:
            #Car entered ROI
            json_message["status"] = "001"
            self.in_lane = True
            self.out_lane = False
            
        if self.connect and json_message["status"] != "000":
            json_message["vehicle_id"] = self.get_buffer_position()
            self.__send_json_message(json_message)
        
        if json_message["status"] != "000":
            print(json_message)
            print(self.__create_track_string(json_message))

    def __send_json_message(self, msg):
        """
            sends json message to specified server 's'
        """
        to_send = self.__create_track_string(msg)
        try:
            self.conn.sendall(to_send)
            print(f"message sent at time {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        except (BrokenPipeError, ConnectionResetError) as e:
            log.error(f'{e} on Station {self.name} - Storing Message')
            self.resend_message = msg
            raise BrokenPipeError 

