import time
import socket 
import json
from collections import deque
import pickle
from datetime import datetime, timezone
import pytz
import subprocess

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
        
        self.offset = int(subprocess.check_output("./timezone.sh").strip()) # gets timezone diff in seconds from utc

        # set Track connection up
        if self.connect:
            self.set_track()
        
        self.pickle_car_count = "car_count.pb"
        # JSON Logging related variables
        self.min_frames = 5
        ###self.car_count = 0
        self.car_count = self.load(self.pickle_car_count)
        self.car_counts = deque([-1]*self.min_frames)
        self.in_lane = False
        self.out_lane = True
        self.total_cars_count = 0
        self.first = 0
        self.prev = 0

    def save(self, file_name, obj):
        with open(file_name, 'wb') as fobj:
            pickle.dump(obj, fobj)

    def load(self, file_name):
        try:
            with open(file_name, 'rb') as fobj:
                return pickle.load(fobj)
        except:
            print(f"[INFO] Failed to Load {file_name}")
            return 0

    def set_track(self):
        print("[INFO] Searching for Delphi Track...")
        print(f"[INFO] Hostname: {socket.gethostname()}")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((self.HOST, self.PORT))
        self.s.listen(1)
        self.conn, self.addr = self.s.accept()
        print("[INFO] Found Delphi Track - Connection from: " + str(self.addr))

    def __create_track_string(self, json_msg):
        '''
            Creates bit string for Delphi Track system
        '''
        loop_num = '001'
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
        '''
            Method sends json messages whenever a car is detected and enough frames have passed
            User can determine how many frames should pass before a message is sent by modifying
            the variable min_frames above
            Parameters:
            numCars: the number of cars detected in the frame by the model
        '''

        # Gets current time in epoch from Jan 1 1970 in utc
        # s1 = int(time.time())

        s1 = int(time.time()) + self.offset # epoch time + timezone difference in seconds 
        #s1 = int(time.time()) - 25200 # utc to pst time

        json_message = {
                "camera_id": "N/A",
                "timestamp":s1,
                "vehicle_id": self.car_count+1,
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
            self.car_count += 1

            if self.car_count >= 99999:
                self.car_count = 0

            self.save(self.pickle_car_count, self.car_count)
            
            print(json_message)
            print(self.__create_track_string(json_message))
            self.out_lane = True
            self.in_lane = False
            #with open('log.txt', 'a') as file:
            #    file.write(json.dumps(json_message))

        elif self.car_counts == (deque([1]*self.min_frames)) and self.out_lane:
            #Car entered ROI
            json_message["status"] = "001"
            print(json_message)
            print(self.__create_track_string(json_message))
            self.in_lane = True
            self.out_lane = False
            #with open('log.txt', 'a') as file:
            #    file.write(json.dumps(json_message))
        
        if self.connect:
            self.__send_json_message(json_message)

    def __send_json_message(self, msg):
        '''
            sends json message  to specified server 's'
        '''
        if msg["status"] != "000":
            #data = json.dumps(msg)
            to_send = self.__create_track_string(msg)
            #s.sendall(bytes(data,encoding="utf-8"))
            self.conn.sendall(to_send)
            #server.sendto(to_send, ('255.255.255.255', 5000))
            print(f"message sent at time {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
