#!/usr/bin/env python3

### python-packages
from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime
import argparse
import imutils

### local-packages
import pickle_util
from find_intersect import intersection_of_polygons
from runtrack import DTrack, DConnect
from runoak import Oak
from logger import *

class OakSim():

    def __init__(self, name = "OAK1", deviceID = None, save_record = None, play_video = None, speed = 1, skip = 0):
        self.name = name
        self.deviceID = deviceID
        self.save_video = save_record
        self.play_record = play_video
        self.speed = int(speed)
        self.skip = int(int(skip) / self.speed)
        
        if self.play_record != None:
            self.play_record = str((Path(__file__).parent / Path(self.play_record)).resolve().absolute())
        
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
        found, device_info = dai.Device.getDeviceByMxId(self.deviceID)
        self.device = dai.Device(self.pipeline, device_info)
        self.qVideo, self.qRgb, self.qDet, self.qIn_Frame = self.start_pipeline()
        
        if self.save_video != None:
            self.video_buffer = cv2.VideoWriter(f"recording/{self.deviceID}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.mp4", cv2.VideoWriter_fourcc(*'mp4v'), 30, self.preview_size)
            print(f"[INFO] Recording Video of {self.deviceID}")
        
        if self.play_record != None:
            self.cap = cv2.VideoCapture(self.play_record)
                
    def define_pipeline(self):
        """
            OAK camera requires a pipeline. Camera input is passed to the neural network.
            Output is the NN bboxes + the 300x300 and 16x9 camera views
        """
        # Create pipeline
        pipeline = dai.Pipeline()

        # Define sources and outputs
        if self.play_record == None:
            cam = pipeline.createColorCamera()
        else:
            xinFrame = pipeline.createXLinkIn()
            xinFrame.setStreamName("inFrame")
        nn = pipeline.createMobileNetDetectionNetwork()
        manip_crop = pipeline.create(dai.node.ImageManip)

        xoutVideo = pipeline.createXLinkOut() # new
        xoutFrame = pipeline.createXLinkOut()
        xoutNN = pipeline.createXLinkOut()

        xoutVideo.setStreamName("video") # new
        xoutFrame.setStreamName("rgb")
        xoutNN.setStreamName("nn")

        # Properties
        if self.play_record == None:
            cam.setPreviewKeepAspectRatio(True)
            cam.setInterleaved(False)
            cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P) # options - THE_1080_P, THE_4_K, THE_12_MP
            cam.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)
        
            if self.save_video == '360p':
                self.preview_size = (640, 360)
            elif self.save_video == '720p':
                self.preview_size = (1280, 720)
            elif self.save_video == '1080p':
                self.preview_size = (1920, 1080)
            else:
                self.preview_size = (640, 360)
        
            print(f"[INFO] Preview Size - {self.preview_size}")
        
            cam.setPreviewSize(self.preview_size[0], self.preview_size[1])
		
        # Define a neural network that will make predictions based on the source frames
        nn.setBlobPath(self.nnPath)
        nn.setConfidenceThreshold(0.7)
        nn.setNumInferenceThreads(2)
        nn.input.setBlocking(False)

        manip_crop.initialConfig.setResize(300, 300)
        manip_crop.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)

        # Linking
        if self.play_record == None:
            cam.preview.link(manip_crop.inputImage)
            cam.preview.link(xoutVideo.input)
        else:
            xinFrame.out.link(manip_crop.inputImage)
            xinFrame.out.link(xoutVideo.input)
        
        manip_crop.out.link(nn.input)
        manip_crop.out.link(xoutFrame.input)
        
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
        qIn_Frame = None
        
        if self.play_record != None:
            qIn_Frame = self.device.getInputQueue(name="inFrame", maxSize=4, blocking=False)
            
        return (qVideo, qRgb, qDet, qIn_Frame)
    
            
    def inference(self, show_display = False):
        """
            Request request frames and detections
            Check if drawroi.py is in use
        """
        if self.play_record != None:
            if self.cap.isOpened():
                
                if self.skip > 0:
                    read_correctly, record_frame = True, self.frame
                    self.skip -= 1
                else:
                    for i in range(self.speed):
                        read_correctly, record_frame = self.cap.read()
                    
                if read_correctly:
                    self.video = record_frame
                    record_height, record_width, _ = record_frame.shape
                    img = dai.ImgFrame()
                    img.setData(self.to_planar(record_frame, (300, 300))) # tried (record_height, record_width) 
                    img.setTimestamp(time.monotonic())
                    img.setWidth(300) # tried record_width
                    img.setHeight(300) # tried record_height
                    img.setType(dai.ImgFrame.Type.BGR888p)
            
                    # Use input queue to send video frame to device
                    self.qIn_Frame.send(img)
                else:
                    raise EOFError
        
        inVideo = self.qVideo.tryGet() # new
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()

        if inVideo is not None: # new
            
            if self.play_record == None:
                self.video = inVideo.getCvFrame() # new
            
            if self.save_video != None:
                self.video_buffer.write(self.video)
        
        if inRgb is not None:
            self.frame = inRgb.getCvFrame()

        if inDet is not None:
            self.detections = inDet.detections
            self.counter += 1

        self.check_drawroi() # stores frame for use in drawroi.py

    def release_resources(self):
        # release video buffer to save video
        if self.save_video != None:
            self.video_buffer.release()
            print(f"[INFO] Released Video Object of {self.deviceID}")

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
            cv2.imshow(f"debug - {self.deviceID}", self.debugFrame) # cv2.resize(self.debugFrame,None,fx=1.45, fy=1.45))
            #cv2.imshow("rgb - {self.deviceID}", cv2.resize(self.frame,None,fx=1.5, fy=1.5))
            #cv2.imshow(f"video - {self.deviceID}", self.video) # imutils.resize(self.video, height=300)) # cv2.resize(self.video,None,fx=0.4, fy=0.4)) # new

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
                
                #print(f"{'1 ROI' if in_roi else '0 ROI'} {self.labelMap[detection.label]} {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        self.car_count = car_count
        
        return frame
        
    def processFrameROI(self, frame):
        """
            Draws ROI on frame
            frame: to-be debug frame
            return: frame
        """
        artifact_color = (255,0,0)
        # draw ROI
        cv2.polylines(frame, [np.asarray(self.ROI, np.int32).reshape((-1,1,2))], True, artifact_color, 2)
        
        return frame

    def processFrameText(self, frame):
        """
            Adds NN fps and NUMCAR text to frame
            frame: to-be debug frame
            return: frame 
        """
        artifact_color = (255,0,0)
	# show NN FPS
        cv2.putText(frame, "NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
                                (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = artifact_color)

        cv2.putText(frame, "NUMCAR: {}".format(self.car_count), (2, 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color = artifact_color)

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
    
    def to_planar(self, arr: np.ndarray, shape: tuple) -> np.ndarray:
        #return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()
        return self.center_crop(arr, shape).transpose(2, 0, 1).flatten()
    
    def center_crop(self, img, dim):
	    """Returns center cropped image
	        Args:
	        img: image to be center cropped
	        dim: dimensions (width, height) to be cropped
	    """
	    width, height = img.shape[1], img.shape[0]
	    mid_x, mid_y = int(width/2), int(height/2)
	    crop_img = img[:, mid_x-mid_y:mid_x+mid_y] # width is center cropped to height
	    crop_img = cv2.resize(crop_img, dim) # 1:1 aspect ratio image is scaled to dim
	    
	    return crop_img
    
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
    parser.add_argument('-record', '--record', choices=['360p', '720p', '1080p'], default = None, help="Save recording of all connected OAK")
    parser.add_argument('-video', '--video', action="store_true", default = None, help="Run Video as Input")
    parser.add_argument('-speed', '--speed', default = 1, type = int, help="Speed of Video Playback - Default: 1")
    parser.add_argument('-skip', '--skip', default = 0, type = int, help="Frames to delay video playback - Compounded with # of OAK")
    args = parser.parse_args()
    
    if args.video == True:
       #args.video = './OAK_Course_Examples/videos/video123-small-10fps.mp4'
       args.video = './OAK_Course_Examples/videos/video08312021.mp4' 
    
    oak_device_ids = [device_info.getMxId() for device_info in dai.Device.getAllAvailableDevices()]
    print(f"[INFO] Found {len(oak_device_ids)} OAK DEVICES - {oak_device_ids}")
    pickle_util.save("storage-oak/device_id.pb", oak_device_ids)
    assert len(oak_device_ids) != 0
    
    dconn = DConnect(connect = args.delphitrack)
    camera_track_list = []
        
    for count, device_id in enumerate(oak_device_ids):
        station = pickle_util.load(f"storage-oak/station_{device_id}.pb", error_return = '255')
        print(f"[INFO] OAK DEVICE: {device_id} - STATION: {station}")
        if station in ['255']:
            log.error(f"Invalid Station {station} - Abort {device_id} Initialization")
            continue
        cam = OakSim(deviceID = device_id, save_record = args.record, play_video = args.video, speed = args.speed, skip = args.skip*count)
        tck = DTrack(name = station, connect = dconn.get_conn())
        camera_track_list.append((cam, tck))
    
    videoComplete = [] # store finished OAK videos
    
    while True:
        try:
            for (camera, track) in camera_track_list:
                camera.inference()
                numCars = camera.detect_intersections(show_display = True)
                track.log_car_detection(numCars)
        
            if cv2.waitKey(1) == ord('q'):
                break 
        
        except KeyboardInterrupt:
            print(f"[INFO] Keyboard Interrupt")
            break 
        
        except EOFError:
            if camera.deviceID not in videoComplete:
                print(f"[INFO] End of Video for {camera.deviceID}")
                videoComplete.append(camera.deviceID)
                if len(videoComplete) == len(camera_track_list):
                    break
            

    dconn.close_socket()
    
    for (camera, track) in camera_track_list:
        camera.release_resources()
