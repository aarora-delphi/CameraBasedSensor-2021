# Python-specific imports
from flask import Flask, request, render_template, Response, flash
from datetime import datetime
import cv2
import threading
import socket  
import json
from collections import deque

from datetime import datetime
import time
import argparse
import numpy as np
import time

import pdb

from os import listdir
from os.path import isfile, join

# Package-specific imports
from camera import Camera
from video import Video
from utils import *
from oak import Oak

#Socket Vars
HOST = "0.0.0.0"
#HOST = 'localhost'
PORT = 5000

TRACK = False

def set_track():
    global TRACK, s, conn, addr

    if TRACK:
        print(socket.gethostname())
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        conn, addr = s.accept()
        print("Connection from: " + str(addr))

#udp option:
#server  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
#server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
#server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
#server.settimeout(0.2)

# Threading variables
data_lock = threading.Lock()
ACTIVE_YOLO_THREAD = False

# Global variables
detection_algo = None
camera_dictionary = {}

current_camera = None

# Debug Frame 
DEBUG_FRAME = np.ones([100,100,3],dtype=np.uint8)  * 155

# JSON Logging related global variables.
min_frames = 5
car_counts = deque([-1]*min_frames)
in_lane = False
out_lane = True
total_cars_count = 0
first = 0
prev = 0

# Main Flask used for routing.
app = Flask(__name__)
app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def __create_track_string(json_msg):
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

def __log_car_detection(numCars):
    '''
        Method sends json messages whenever a car is detected and enough frames have passed
        User can determine how many frames should pass before a message is sent by modifying
        the variable min_frames above
        Parameters:
        numCars: the number of cars detected in the frame by the model
    '''
    global in_lane
    global out_lane
    global min_frames

    # Gets current time in epoch from Jan 1 1970
    s1 = int(time.time())

    json_message = {
            "camera_id": current_camera,
            "timestamp":s1,
            "vehicle_id": camera_dictionary[current_camera].car_count+1,
            "status": "000"
    }

    if numCars is None or min_frames < 1:
        print(json_message)
        return

    car_counts.append(numCars)
    car_counts.popleft()

    if car_counts == (deque([0]*min_frames)) and in_lane:
        #Car left ROI
        json_message["status"] = "002"
        camera_dictionary[current_camera].car_count += 1
        print(json_message)
        print(__create_track_string(json_message))
        out_lane = True
        in_lane = False
        #with open('log.txt', 'a') as file:
        #    file.write(json.dumps(json_message))

    elif car_counts == (deque([1]*min_frames)) and out_lane:
        #Car entered ROI
        json_message["status"] = "001"
        print(json_message)
        print(__create_track_string(json_message))
        in_lane = True
        out_lane = False
        #with open('log.txt', 'a') as file:
        #    file.write(json.dumps(json_message))
    return json_message 

def __send_json_message(msg):
    '''
        sends json message  to specified server 's'
    '''
    if msg["status"] != "000":
        #data = json.dumps(msg)
        to_send = __create_track_string(msg)
        #s.sendall(bytes(data,encoding="utf-8"))
        conn.sendall(to_send)
        #server.sendto(to_send, ('255.255.255.255', 5000))
        print("message sent")


def __perform_detection(frame):
        """
                Kickstarts the yolo algorithm detection on the given frame. This is run on a thread concurrent to the main server.
        """

        global ACTIVE_YOLO_THREAD
        global total_cars_count
        global detection_algo
        global DEBUG_FRAME
        global TRACK

        with data_lock:
                detection_algo.set_frame_and_roi(frame, camera_dictionary[current_camera]) 
                numCars, detection_debug_frame = detection_algo.detect_intersections() 
                DEBUG_FRAME = detection_debug_frame
                json_dict = __log_car_detection(numCars)
                #send_string = __create_track_string(json_dict)

                if TRACK:                
                        __send_json_message(json_dict)
        
                if numCars > 0:
                        total_cars_count += numCars
                        
        ACTIVE_YOLO_THREAD = False


def __get_frames():
        """
                Generator function to get frames constantly to the frontend and to kickstart the detection on each frame.
        """
        global thread, ACTIVE_YOLO_THREAD
        for frame in camera_dictionary[current_camera]:
                roi = camera_dictionary[current_camera].ROI

                # Check to make sure that the current camera has a specified ROI and that there's no thread running.
                if roi and not ACTIVE_YOLO_THREAD:
                        thread = threading.Thread(target=__perform_detection,args=(frame,), daemon = True)
                        thread.start()
                        ACTIVE_YOLO_THREAD = True

                yield(prepare_frame_for_display(frame, current_camera))
                
def __get_debug_frames():
        """
                Generator function to show debug frames to frontend
        """
        global DEBUG_FRAME
        
        while True:
                time.sleep(0.01)
                yield(prepare_frame_for_display(DEBUG_FRAME, current_camera))

@app.route('/')
def show_stream():
        """
                Function called when Flask boots up for the first time.
        """
        return render_template('show_stream.html', camera_dict=camera_dictionary, current_camera=current_camera)

@app.route("/stream_feed")
def stream_feed():
        """
                Utilizes the generator function main.py::__get_frames() to send frames from the current_camera stream into the frontend.
        """
        return Response(__get_frames(), mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/debug_feed")
def debug_feed():
        """
                Utilizes the generator function main.py::__get_frames() to send frames from the current_camera stream into the frontend.
        """
        return Response(__get_debug_frames(), mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route('/record_roi', methods=['POST'])
def record_roi():
        """
                Updates the current camera stream's ROI coordinates.
        """
        print("RECEIVED ROI")

        roi_coord_is_NaN = False

        roi_coord = []
        for rc in range(len(request.form)//2): # translate the received ROI in request.form into a Python list of coordinates
                x_coord, y_coord = request.form["roi_coord[{}][x]".format(rc)], request.form["roi_coord[{}][y]".format(rc)]
                
                if x_coord == "NaN" or y_coord == "NaN":
                        roi_coord_is_NaN = True
                        break
                else:
                        roi_coord.append([int(x_coord), int(y_coord)])
        
        #print(roi_coord)

        if is_valid_roi(roi_coord) and not roi_coord_is_NaN: # validate the ROI coordinates
                print("VALID ROI SPECIFIED")
                camera_dictionary[current_camera].set_roi_coordinates(roi_coord)
        
        if not is_valid_roi(roi_coord):
                print("INVALID ROI: MUST SPECIFY POLYGON")

        return render_template('show_stream.html', camera_dict=camera_dictionary, current_camera=current_camera)

@app.route('/choose_camera', methods=['POST'])
def choose_camera():
        """
                Switches the camera stream that's being displayed on the frontend.
        """
        global current_camera
        current_camera = request.form["camera_view"]

        if current_camera == '0':
                current_camera = 0

        print("CURRENT CAMERA IS NOW {}".format(current_camera))

        return render_template('show_stream.html', camera_dict=camera_dictionary, current_camera=current_camera)

@app.route('/add_camera', methods=['POST'])
def add_camera():
        """
                Adds a new camera to the system with the user specified camera url.
        """

        camera_name = request.form["camera_name"]
        camera_url = request.form["stream_url"]

        # Special case which indicates the computer's webcam
        if camera_url == "0":
                camera_url = 0

        if camera_name not in camera_dictionary:
                camera_dictionary[camera_name] = Camera(camera_url)
        else:
                print("ERROR: CAMERA EXISTS")

        return render_template('show_stream.html', camera_dict=camera_dictionary, current_camera=current_camera)

@app.route('/remove_camera', methods=['POST'])
def remove_camera():
        """
                Removes a camera from the system and ends the camera's video stream.
        """
        camera_name = request.form["remove_name"]

        if camera_name in camera_dictionary:
                camera_dictionary[camera_name].stop_video_stream()
                del(camera_dictionary[camera_name])

                # If the camera being removed was the current camera, set a new camera stream to display onto the frontend
                if camera_dictionary and current_camera == camera_name:
                        current_camera = next(camera_dictionary)

        else:
                print("INVALID ENTRY: CAMERA NAME TO REMOVE DOES NOT EXIST")

        return render_template('show_stream.html', camera_dict=camera_dictionary, current_camera=current_camera)

def __parseArguments():
        """Choose arguments to run flask application. Arguments are --model and --webcam"""
        global camera_dictionary
        global detection_algo
        global current_camera
        global TRACK
        
        parser = argparse.ArgumentParser("Run Detection Flask App")
        parser.add_argument("--model", default="cpu-tiny-yolov3", help="Model to load. Choose between cpu-yolov3, cpu-tiny-yolov3, tpu-tiny-yolov3, tpu-mobilenetv2")
        parser.add_argument("--input", default="video", help="Type webcam for webcam, camera for default IP cameras, oak for oak-1 camera, or video path for video input")
        parser.add_argument("--track", default="false", help="For enabling the track system. Choose between true or false")
        args = parser.parse_args()
        
        if args.track == "true":
            TRACK = True
        elif args.track == "false":
            TRACK = False
        
        if args.model == "cpu-tiny-yolov3" or args.model == "cpu-yolov3":
                from YoloVideo import YoloVideo
                detection_algo = YoloVideo(initialize_yolo(modelType=args.model))

        elif args.model == "tpu-tiny-yolov3" or args.model == "tpu-mobilenetv2":
                from tpuVideo import tpuVideo
                detection_algo = tpuVideo(initialize_tpu(modelType=args.model), modelType=args.model)
        
        if args.input == "webcam":
                first_camera = 0 
                camera_dictionary[first_camera] = Camera(first_camera)
        
        elif args.input == "camera":
                first_camera = 'rtsp://admin:12345@172.16.15.12'
                camera_dictionary[first_camera] = Camera(first_camera)

                second_camera = 'rtsp://admin:!hylanD3550@172.16.15.11:554/1/h264major'
                camera_dictionary[second_camera] = Camera(second_camera)
        
        elif args.input == "oak":
                first_camera = 'OAK1'
                camera_dictionary[first_camera] = Oak(first_camera)
        
        elif args.input == "video":
                video_folder = "./inputVideos"
                only_vfiles = [join(video_folder, f) for f in listdir(video_folder) if isfile(join(video_folder, f))]
                                
                # create Video object for each .mp4 video
                for vfile in only_vfiles:
                    camera_dictionary[vfile] = Video(vfile)
                
                first_camera = only_vfiles[0]

        else:
                first_camera = args.webcam
                camera_dictionary[first_camera] = Video(first_camera)
 
        current_camera = first_camera

                
if __name__ == "__main__":
        __parseArguments()
        set_track()
        
        app.run(host="0.0.0.0", port=2000,  debug=False)
        
        if TRACK:
            s.close()
