#!/usr/bin/env python3

### python-packages
from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime
import argparse

### local-packages
import pickle_util
from find_intersect import intersection_of_polygons
from runtrack import DTrack

class Oak():

    def __init__(self, name = "OAK1", deviceID = None):
        self.name = name
        self.deviceID = deviceID
        
        self.drawroi_running = False
        
        self.ROI = [[50, 50], [250, 50], [250, 250], [50, 250]] # sample ROI
        self.set_roi() # sets last saved ROI
        self.car_count = 0
        
        model_location = './OAK_Course_Examples/models/OpenVINO_2021_2/mobilenet-ssd_openvino_2021.2_6shave.blob'
        self.nnPath = str((Path(__file__).parent / Path(model_location)).resolve().absolute())

        # MobilenetSSD class labels
        self.labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", 
                    "bottle", "bus", "car", "cat", "chair", "cow", \
                    "diningtable", "dog", "horse", "motorbike", "person", \
                    "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

        self.startTime = time.monotonic()
        self.counter = 0
        self.detections = []
        
        self.video = np.zeros([300,300,3],dtype=np.uint8) # new
        self.frame = np.zeros([300,300,3],dtype=np.uint8)
        self.debugFrame = None

        self.pipeline = self.define_pipeline()
        self.device = dai.Device(self.pipeline)
        self.qVideo, self.qRgb, self.qDet = self.start_pipeline()

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

        xoutVideo = pipeline.createXLinkOut() # new
        xoutFrame = pipeline.createXLinkOut()
        xoutNN = pipeline.createXLinkOut()

        xoutVideo.setStreamName("video") # new
        xoutFrame.setStreamName("rgb")
        xoutNN.setStreamName("nn")

        # Properties
        cam.setPreviewKeepAspectRatio(True)
        cam.setPreviewSize(300, 300)
        cam.setInterleaved(False)
        # available resolutions are THE_1080_P (default), THE_4_K, THE_12_MP
        # cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
		
        # Define a neural network that will make predictions based on the source frames
        nn.setBlobPath(self.nnPath)
        nn.setConfidenceThreshold(0.7)
        nn.setNumInferenceThreads(2)
        nn.input.setBlocking(False)

        # Linking
        cam.video.link(xoutVideo.input) # new
        cam.preview.link(xoutFrame.input)
        cam.preview.link(nn.input)
        nn.out.link(xoutNN.input)
        
        return pipeline

    def start_pipeline(self):
        """
            Output Queues used for requesting frame and detections
        """
        print("[INFO] Starting OAK Pipeline...")
        # Start pipeline
        self.device.startPipeline()

        # Output queues will be used to get the rgb frames and nn data from the
        # output streams defined above.
        qVideo = self.device.getOutputQueue(name="video", maxSize=4, blocking=False) # new
        qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)
            
        return (qVideo, qRgb, qDet)
            
    def inference(self, show_display = False):
        """
            Request request frames and detections
            Check if drawroi.py is in use
        """
        inVideo = self.qVideo.tryGet() # new
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()

        if inVideo is not None: # new
            self.video = inVideo.getCvFrame() # new
        
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
                print("[INFO] drawroi app in use - saving frames")
            elif is_running == False and self.drawroi_running == True:
                print("[INFO] drawroi app closed - stopped saving frames")
            
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
            cv2.imshow("debug", cv2.resize(self.debugFrame,None,fx=1.45, fy=1.45))
            #cv2.imshow("rgb", cv2.resize(self.frame,None,fx=1.5, fy=1.5))
            cv2.imshow("video", cv2.resize(self.video,None,fx=0.4, fy=0.4)) # new

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
            if self.labelMap[detection.label] in ["car", "motorbike", "person"]:
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
                
                #print(f"{'1 ROI' if in_roi else '0 ROI'} {self.labelMap[detection.label]} {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        self.car_count = car_count
        
        return frame
        
    def processFrameROI(self, frame):
        """
            Draws ROI on frame
            frame: to-be debug frame
            return: frame
        """
        # draw ROI
        cv2.polylines(frame, [np.asarray(self.ROI, np.int32).reshape((-1,1,2))], True, (255,255,255), 2)
        
        return frame

    def processFrameText(self, frame):
        """
            Adds NN fps and NUMCAR text to frame
            frame: to-be debug frame
            return: frame 
        """
		# show NN FPS
        cv2.putText(frame, "NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
                                (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color=(255, 255, 255))

        cv2.putText(frame, "NUMCAR: {}".format(self.car_count), (2, 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color=(255, 255, 255))

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

#### testing below ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-track', '--delphitrack', action="store_true", help="Send messages to track system")
    args = parser.parse_args()
    
    oak_device_ids = [device_info.getMxId() for device_info in dai.Device.getAllAvailableDevices()]
    pickle_util.save("storage-oak/device_id.pb", oak_device_ids)
    assert len(oak_device_ids) != 0
    
    camera_list = []
    for device_id in oak_device_ids:
        camera_list.append(Oak(deviceID = device_id))
    
    #camera1 = Oak(deviceID = oak_device_ids[0])
    track1 = DTrack(connect = args.delphitrack) # only one instance needed
    
    while True:
        try:
            for camera in camera_list:
                camera.inference()
                numCars = camera.detect_intersections(show_display = True)
                track1.log_car_detection(numCars) # TODO: add vehicle_id
        
            if cv2.waitKey(1) == ord('q'):
                break 
        
        except KeyboardInterrupt:
            print(f"[INFO] Keyboard Interrupt")
            break  

    track1.close_socket()
    
