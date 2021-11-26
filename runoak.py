#!/usr/bin/env python3

### python-packages
from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
import argparse
import multiprocessing
import redis

### local-packages
import pickle_util
from find_intersect import intersection_of_polygons
from runtrack import DTrack
from synctrack import synctrackmain
from logger import *

class Oak():

    def __init__(self, name = "OAK1", deviceID = None):
        self.name = name
        self.deviceID = deviceID
        self.station = pickle_util.load(f"storage-oak/station_{self.deviceID}.pb", error_return = '255')
        self.drawroi_running = False
        self.lensPosition = None
        
        self.ROI = [[50, 50], [250, 50], [250, 250], [50, 250]] # sample ROI
        self.set_roi() # sets last saved ROI
        self.car_count = 0
        self.error_flag = 0
        
        model_location = './model/mobilenet-ssd_openvino_2021.2_6shave.blob'
        self.nnPath = str((Path(__file__).parent / Path(model_location)).resolve().absolute())

        # MobilenetSSD class labels
        self.labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", \
                    "bottle", "bus", "car", "cat", "chair", "cow", \
                    "diningtable", "dog", "horse", "motorbike", "person", \
                    "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

        self.detections = []
        self.frame = np.zeros([300,300,3],dtype=np.uint8)
        self.debugFrame = np.zeros([300,300,3],dtype=np.uint8)
        
        self.r = redis.StrictRedis()
        self.event = None

    def organize_pipeline(self):
        """
            OAK Pipeline is defined, Device is found, and Pipeline is started 
        """
        self.pipeline = self.define_pipeline()
        found, self.device_info = dai.Device.getDeviceByMxId(self.deviceID)
        self.device = dai.Device(self.pipeline, self.device_info)
        self.start_pipeline()        

    def define_pipeline(self):
        """
            OAK camera requires a pipeline. Camera input is passed to the neural network.
            Output is the NN bboxes + the 300x300 and 16x9 camera views
        """
        # Create pipeline
        pipeline = dai.Pipeline()

        # Define sources and outputs
        cam = pipeline.createColorCamera()
        nn = pipeline.createMobileNetDetectionNetwork()

        controlIn = pipeline.createXLinkIn()
        configIn = pipeline.createXLinkIn()
        xoutFrame = pipeline.createXLinkOut()
        xoutNN = pipeline.createXLinkOut()

        controlIn.setStreamName('control')
        configIn.setStreamName('config')
        xoutFrame.setStreamName("rgb")
        xoutNN.setStreamName("nn")

        # Properties
        cam.setPreviewKeepAspectRatio(True)
        cam.setPreviewSize(300, 300)
        cam.setInterleaved(False)
        cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P) # THE_1080_P, THE_4_K, THE_12_MP
        cam.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)
        nn.setBlobPath(self.nnPath)
        nn.setConfidenceThreshold(0.8)
        nn.setNumInferenceThreads(2)
        nn.input.setBlocking(False)

        # Linking
        controlIn.out.link(cam.inputControl)
        configIn.out.link(cam.inputConfig)
        cam.preview.link(xoutFrame.input)
        cam.preview.link(nn.input)
        nn.out.link(xoutNN.input)
        
        return pipeline

    def start_pipeline(self):
        """
            Output Queues used for requesting frame and detections
        """
        log.info("Starting OAK Pipeline...")

        # Output queues get the rgb frames and nn data from the defined output streams.
        self.controlQueue = self.device.getInputQueue('control')
        self.configQueue = self.device.getInputQueue('config')
        self.qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)
    
        self.startTime = time.monotonic()
        self.counter = 0
        self.set_autofocus()
    
    def set_autofocus(self):
        """
            Set the lens position for Manual Focus
            If no lensPosition set then default is continuous autofocus
        """
        lensPosition = pickle_util.load(f"storage-oak/focus_{self.deviceID}.pb", error_return = None)
        
        if lensPosition == self.lensPosition:
            return
        
        if type(lensPosition) == int and lensPosition >= 0 and lensPosition <= 255:
            self.lensPosition = lensPosition
            log.info(f"Manual Focus set to {lensPosition} for {self.deviceID}")
            ctrl = dai.CameraControl()
            ctrl.setAutoFocusMode(dai.CameraControl.AutoFocusMode.OFF)
            ctrl.setManualFocus(lensPosition)
            self.controlQueue.send(ctrl)
            time.sleep(0.50) # send control twice for assurance
            self.controlQueue.send(ctrl)
        
        elif type(lensPosition) == int and lensPosition == -1:
            self.lensPosition = lensPosition
            log.info(f"Autofocus Set for {self.deviceID}")
            ctrl = dai.CameraControl()
            ctrl.setAutoFocusMode(dai.CameraControl.AutoFocusMode.CONTINUOUS_VIDEO)
            self.controlQueue.send(ctrl)
            
          
    def inference(self):
        """
            Request request frames and detections
            Check if drawroi.py is in use
        """
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()
        
        if inRgb is not None:
            self.frame = inRgb.getCvFrame()

        if inDet is not None:
            self.detections = inDet.detections
            self.counter += 1

        self.check_drawroi() # stores frame for use in drawroi.py

    def check_drawroi(self):
        """
            Stores frames for drawroi.py during specified intervals below
        """
        if self.counter % 450 == 0: # check every ~15 seconds if drawroi app is in use
            is_running = pickle_util.load("storage-oak/drawroi_running.pb", error_return = False)
            
            if is_running == True and self.drawroi_running == False:
                log.info("drawroi app in use - saving frames")
            elif is_running == False and self.drawroi_running == True:
                log.info("drawroi app closed - stopped saving frames")
            
            self.drawroi_running = is_running
        
        if self.drawroi_running:
            if self.counter % 30 == 0: # perform action every ~1 second
                #cv2.imwrite(f"storage-oak/{self.deviceID}.png", self.frame) # save frame
                #cv2.imwrite(f"storage-oak/{self.deviceID}.png", self.debugFrame) # save debug frame
                self.set_roi()
                self.set_autofocus()
    
    def set_roi(self):
        """
            Sets last saved ROI from drawroi.py to self.ROI
        """
        app_roi = pickle_util.load("storage-oak/canvas_roi.pb", error_return = {})
        if self.deviceID in app_roi:
            self.ROI = self.convert_tlbr_to_list(app_roi[self.deviceID][0])
  
    def detect_intersections(self, show_display = False):
        """
            Creates Debug Frame and returns number of detections in ROI
            show_display: bool - if true, shows debug and 16/9 view
        """

        self.processFrame() # determines if bbox in ROI + creates debug frame
        
        if show_display:
            cv2.imshow(f"{self.station} - {self.deviceID}", self.debugFrame) #cv2.resize(self.debugFrame,None,fx=1.45, fy=1.45))
            #cv2.imshow("rgb - {self.deviceID}", cv2.resize(self.frame,None,fx=1.5, fy=1.5))
            ### cv2.imshow(f"video - {self.deviceID}", cv2.resize(self.video,None,fx=0.4, fy=0.4)) # new

        if self.counter % 5 == 0:
            # testing redis
            retval, buffer = cv2.imencode('.png', self.debugFrame)
            img_bytes = np.array(buffer).tobytes()
            self.r.set(self.deviceID, img_bytes)

        return self.car_count 
        
    def processFrame(self):
        """
            Creates the debug frame
        """
        frame = self.frame.copy()
        frame = self.processFrameBBOX(frame) # determines if bbox in ROI + adds BBOX to debug frame
        frame = self.processFrameROI(frame) # adds ROI to debug frame
        frame = self.processFrameText(frame) # adds text to debug frame
        
        self.debugFrame = frame

    def processFrameBBOX(self, frame):
        """
            Loops through OAK NN detections and determines if bbox in ROI
            If in ROI, draws green bbox on frame, else draws red bbox on frame
            frame: to-be debug frame
            return: frame
        """
        car_count = 0
        
        for detection in self.detections:
    
            bbox_color = (0,0,255) # red
            
            # address bbox with correct label
            if self.labelMap[detection.label] in ["car", "motorbike"]:
                bbox = self.frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))        
                
                in_roi = self.bbox_in_roi(bbox)
                if in_roi:
                    bbox_color = (0,255,0) # green bbox on debug frame
                    car_count += 1
                
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), bbox_color, 2)
                cv2.putText(frame, self.labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), \
                    cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), \
                    cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
        
        self.car_count = car_count
        
        return frame
        
    def processFrameROI(self, frame, color = (255,0,255)):
        """
            Draws ROI on frame
            frame: to-be debug frame
            return: frame
        """
        cv2.polylines(frame, [np.asarray(self.ROI, np.int32).reshape((-1,1,2))], True, color, 2)
        
        return frame

    def processFrameText(self, frame, color = (255,255,255)):
        """
            Adds NN fps and NUMCAR text to frame
            frame: to-be debug frame
            return: frame 
        """
        nn_fps = self.counter / (time.monotonic() - self.startTime)
        
        # Neural Network Inference FPS + CAR Count
        text = f"FPS: {nn_fps:.2f}"
        text_location = (5, 270)
        cv2.putText(frame, text, text_location, cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = (0,0,0), thickness = 6) # border text
        cv2.putText(frame, text, text_location, cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = color)

        # Number of Vehicles in ROI
        text = f"CAR: {self.car_count}"
        text_location = (5, 290)
        cv2.putText(frame, text, text_location, cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = (0,0,0), thickness = 6) # border text
        cv2.putText(frame, text, text_location, cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = color)

        # Event Message
        cv2.putText(frame, self.event, (5, 250), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = (0,0,0), thickness = 6) # border text
        cv2.putText(frame, self.event, (5, 250), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = color)

        return frame

    def update_event(self, event):
        """
            Updates event
        """
        event = event.decode("utf-8").replace("\n", "")
        # station = event[0:3]
        status = "IN" if event[3:6] == "255" else "OUT"
        vehicle_id = event[-5:]
        self.event = f"LAST EVENT: {status} - {vehicle_id}"

    # nn data (bounding box locations) are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(self, frame, bbox):
        """
            Normalizes NN bbox from <0..1> range relative to frame width/height
            frame: to-be debug frame
            bbox: (xmin,ymin,xmax,ymax)
            returns: normalized points
        """
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)
    
    def convert_tlbr_to_list(self, box):
        """
            Converts box to all points in a rectangle
            box: (xmin,ymin,xmax,ymax) - top left bottom right bbox/roi format
            return: rearranged list of points
        """
        point_list =  [ [box[0], box[1]], 
                        [box[2], box[1]],
                        [box[2], box[3]],
                        [box[0], box[3]] 
                      ]
        
        return point_list
        
    def bbox_in_roi(self, bbox):
        """
            Check if BBOX in ROI
            bbox: list - [pt1, pt2, pt3, pt4] where pt# = [x,y]
            return: bool - true if ROI and bbox intersect
        """
        
        pt_mod_bbox = self.convert_tlbr_to_list(bbox)
        try:
            in_roi = intersection_of_polygons(self.ROI, pt_mod_bbox)   
        except:
            in_roi = False
            
        return in_roi

    def release_resources(self):
        """
            Closes the device
        """
        log.info(f"Closing Device {self.deviceID}")
        self.device.close() # close device

def getOakDeviceIds():
    """
        Checks for available OAK Devices
    """
    deviceIds = lambda : [device_info.getMxId() for device_info in dai.Device.getAllAvailableDevices()]
    oak_device_ids = deviceIds()
    while '<error>' in oak_device_ids:
        log.error('Unable to Retrieve OAK Device - Trying Again')
        oak_device_ids = deviceIds()
    return oak_device_ids

def parse_arguments():
    """
        Parses Command Line Arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-track', '--track', action="store_true", help="Send messages to track system")
    args = parser.parse_args() 
    return args

def create_camera_track_list(camera_track_list, args, ignore_station = ['255'], order_station = False):
    """
        Initializes list of Oak and DTrack Objects for each OAK Device
    """
    oak_device_ids = getOakDeviceIds()
    log.info(f"Found {len(oak_device_ids)} OAK DEVICES - {oak_device_ids}")
    pickle_util.save("storage-oak/device_id.pb", oak_device_ids)
    assert len(oak_device_ids) != 0

    def order_oak_by_station(elem):
        station = pickle_util.load(f"storage-oak/station_{elem}.pb", error_return = '255')
        return int(station) if station != '000' else 255

    if order_station:
        oak_device_ids.sort(key=order_oak_by_station)    

    for count, device_id in enumerate(oak_device_ids):
        station = pickle_util.load(f"storage-oak/station_{device_id}.pb", error_return = '255')
        log.info(f"OAK DEVICE: {device_id} - STATION: {station}")
        if station in ignore_station:
            log.error(f"Invalid Station {station} - Abort {device_id} Initialization")
            continue

        cam = getCam(device_id, args, count); cam.organize_pipeline()
        tck = DTrack(name = station, connect = args.track)
        camera_track_list.append([cam, tck])

def getCam(device_id, args, count):
    """
        Returns the Oak Object
    """
    return Oak(deviceID = device_id)    

if __name__ == "__main__":
    log.info("Started runoak Process\n\n")
    time.sleep(8) # allows time for all OAK to be present in autodiscovery
    args = parse_arguments()
    
    if args.track:
        work_queue = multiprocessing.Queue()
        synctck = multiprocessing.Process(target=synctrackmain, args=(work_queue,True), daemon=True)
        synctck.start()
        log.info("Started synctrack Process")
    
    camera_track_list = []
    create_camera_track_list(camera_track_list, args, ignore_station = ['255'], order_station = False)
    should_run = True
    
    while should_run:
        for (camera, track) in camera_track_list:
            try:
                camera.inference()
                numCars = camera.detect_intersections(show_display = True)
                to_send = track.log_car_detection(numCars)
                
                if args.track:
                    if to_send != None:
                        work_queue.put(to_send) 
                        camera.update_event(to_send)
                    
                    if not synctck.is_alive():
                        synctck = multiprocessing.Process(target=synctrackmain, args=(work_queue,False), daemon=True)
                        synctck.start()
                        log.info("Restarted synctrack Process")
                        
        
                if cv2.waitKey(1) == ord('q'):
                    should_run = False; break 
        
            except KeyboardInterrupt:
                log.info(f"Keyboard Interrupt")
                should_run = False; break            
 
            except RuntimeError:
                if camera.error_flag == 0:
                    log.exception(f"Runtime Error for {camera.deviceID}")
                    camera.device.close() # close device
                    camera.error_flag = 1
                if camera.device.isClosed() and camera.deviceID in getOakDeviceIds(): # TO DO - make non-blocking
                    log.info(f"Found {camera.deviceID} - Reconnecting to OAK Pipeline")
                    camera.device = dai.Device(camera.pipeline, camera.device_info)
                    camera.start_pipeline()
                    camera.error_flag = 0
        
            except:
                log.exception(f"New exception")
                should_run = False; break
    
    for (camera, track) in camera_track_list:
        camera.release_resources()
