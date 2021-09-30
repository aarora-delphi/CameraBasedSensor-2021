#!/usr/bin/env python3

### python-packages
from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime
import argparse
import threading
import multiprocessing

### local-packages
import pickle_util
from find_intersect import intersection_of_polygons
from runtrack import DTrack, DConnect
from logger import *
from synctrack import TrackSync, synctrackmain


class Oak():

    def __init__(self, name = "OAK1", deviceID = None):
        self.name = name
        self.deviceID = deviceID
        self.station = pickle_util.load(f"storage-oak/station_{self.deviceID}.pb", error_return = '255')
        self.drawroi_running = False
        
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
        self.debugFrame = None
        ### self.video = np.zeros([300,300,3],dtype=np.uint8) # new

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
        ### xoutVideo = pipeline.createXLinkOut() # new

        controlIn.setStreamName('control')
        configIn.setStreamName('config')
        xoutFrame.setStreamName("rgb")
        xoutNN.setStreamName("nn")
        ### xoutVideo.setStreamName("video") # new

        # Properties
        cam.setPreviewKeepAspectRatio(True)
        cam.setPreviewSize(300, 300)
        cam.setInterleaved(False)
        cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P) # THE_1080_P, THE_4_K, THE_12_MP
        cam.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)
        nn.setBlobPath(self.nnPath)
        nn.setConfidenceThreshold(0.7)
        nn.setNumInferenceThreads(2)
        nn.input.setBlocking(False)

        # Linking
        controlIn.out.link(cam.inputControl)
        configIn.out.link(cam.inputConfig)
        cam.preview.link(xoutFrame.input)
        cam.preview.link(nn.input)
        nn.out.link(xoutNN.input)
        ### cam.video.link(xoutVideo.input) # new
        
        return pipeline

    def start_pipeline(self):
        """
            Output Queues used for requesting frame and detections
        """
        log.info("Starting OAK Pipeline...")
        ### self.device.startPipeline() # Deprecation Warning shown if included

        # Output queues get the rgb frames and nn data from the defined output streams.
        self.controlQueue = self.device.getInputQueue('control')
        self.configQueue = self.device.getInputQueue('config')
        self.qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)
        self.qVideo = None ### self.device.getOutputQueue(name="video", maxSize=4, blocking=False) # new
    
        self.startTime = time.monotonic()
        self.counter = 0
        self.set_autofocus(lensPosition = 150)
    
    def set_autofocus(self, lensPosition = None):
        """
            Set the lens position for Manual Focus
            If no lensPosition set then default is continuous autofocus
            lensPosition: int between 0 and 255 inclusive
        """
        if type(lensPosition) == int:
            log.info(f"Manual Autofocus set to {lensPosition}")
            ctrl = dai.CameraControl()
            ctrl.setManualFocus(lensPosition)
            self.controlQueue.send(ctrl) 
        else:
             log.info(f"Continuous Autofocus Enabled")  
          
    def inference(self, show_display = False):
        """
            Request request frames and detections
            Check if drawroi.py is in use
        """
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()
        ### inVideo = self.qVideo.tryGet() # new
        
        if inRgb is not None:
            self.frame = inRgb.getCvFrame()

        if inDet is not None:
            self.detections = inDet.detections
            self.counter += 1

        ### if inVideo is not None: # new
        ###     self.video = inVideo.getCvFrame() # new

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
                cv2.imwrite(f"storage-oak/{self.deviceID}.png", self.frame)
                self.set_roi()
    
    def set_roi(self):
        """
            Sets last saved ROI from drawroi.py to self.ROI
        """
        app_roi = pickle_util.load("storage-oak/canvas_roi.pb", error_return = {})
        if self.deviceID in app_roi:
            temp_roi = app_roi[self.deviceID][0] # take first entry
            temp_roi = self.convert_tlbr_to_list(temp_roi)
            self.ROI = temp_roi
    
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
        
    def processFrameROI(self, frame, color = (255,0,0)):
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
        
        # Neural Network Inference FPS
        cv2.putText(frame, "FPS: {:.2f}".format(nn_fps),
                                (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = (0,0,0), thickness = 6) # border text
        
        cv2.putText(frame, "FPS: {:.2f}".format(nn_fps), (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = color)

        # Number of Vehicles in ROI
        cv2.putText(frame, "CAR: {}".format(self.car_count), 
                                (2, 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = (0,0,0), thickness = 6) # border text
        
        cv2.putText(frame, "CAR: {}".format(self.car_count), (2, 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = color)

        return frame

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
        log.info(f"Closing Device {self.deviceID}")
        self.device.close() # close device

def getOakDeviceIds():
    deviceIds = lambda : [device_info.getMxId() for device_info in dai.Device.getAllAvailableDevices()]
    oak_device_ids = deviceIds()
    while '<error>' in oak_device_ids:
        log.error('Unable to Retrieve OAK Device - Trying Again')
        oak_device_ids = deviceIds()
    return oak_device_ids

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-track', '--track', action="store_true", help="Send messages to track system")
    args = parser.parse_args() 
    return args

def create_camera_track_list(camera_track_list, args):
    oak_device_ids = getOakDeviceIds()
    log.info(f"Found {len(oak_device_ids)} OAK DEVICES - {oak_device_ids}")
    pickle_util.save("storage-oak/device_id.pb", oak_device_ids)
    assert len(oak_device_ids) != 0
        
    for device_id in oak_device_ids:
        station = pickle_util.load(f"storage-oak/station_{device_id}.pb", error_return = '255')
        log.info(f"OAK DEVICE: {device_id} - STATION: {station}")
        if station in ['255']:
            log.error(f"Invalid Station {station} - Abort {device_id} Initialization")
            continue

        cam = Oak(deviceID = device_id); cam.organize_pipeline()
        tck = DTrack(name = station, connect = dconn.get_conn())
        camera_track_list.append([cam, tck])
    

if __name__ == "__main__":
    args = parse_arguments()
    dconn = DConnect(connect = args.track)
    
    ### testing synctrack
    if args.track:
        synctck = multiprocessing.Process(target=synctrackmain, args=(dconn,True), daemon=True)
        synctck.start()
        log.info("Started synctrack process")
    ###
    
    camera_track_list = []
    create_camera_track_list(camera_track_list, args)
    should_run = True

    while should_run:
        for (camera, track) in camera_track_list:
            try:
                camera.inference()
                numCars = camera.detect_intersections(show_display = True)
                track.log_car_detection(numCars)
        
                if cv2.waitKey(1) == ord('q'):
                    should_run = False; break 
        
            except KeyboardInterrupt:
                log.info(f"Keyboard Interrupt")
                should_run = False; break 
        
            except BrokenPipeError:
                log.error("Lost Connection to Track")

                if args.track:
                    synctck.terminate(); synctck.close()
                    log.info(f"Terminated synctrack Process - {synctck} {synctck.is_alive()}")
                
                dconn.close_socket()
                dconn = DConnect(connect = args.track)
                for i in range(len(camera_track_list)):
                    camera_track_list[i][1].set_connect(dconn.get_conn()) # reset track connection
            
                if args.track:
                    synctck = multiprocessing.Process(target=synctrackmain, args=(dconn,False), daemon=True)
                    synctck.start()
                    log.info("Restarted synctrack Process")              
 
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

    dconn.close_socket()
    
    for (camera, track) in camera_track_list:
        camera.release_resources()
