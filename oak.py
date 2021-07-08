#!/usr/bin/env python3

from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time

from find_intersect import intersection_of_polygons

class Oak():

    def __init__(self, name = "OAK1"):
        self.name = name
        self.ROI = [] # [[421, 197], [632, 73], [482, 331], [134, 332]] # sample ROI
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
        
        self.frame = np.zeros([300,300,3],dtype=np.uint8)
        self.debugFrame = None

        self.pipeline = self.define_pipeline()
        self.device = dai.Device(self.pipeline)
        self.qRgb, self.qDet = self.start_pipeline()
        
        self.identify_stream_dimensions()
            
    def get_frame(self):
        """
        Retrieves next frame - if unavailable returns self.frame
        """
        inRgb = self.qRgb.tryGet()
    
        if inRgb is not None:
            self.frame = inRgb.getCvFrame()
            frame = self.resize_frame_with_border(self.frame)
            return frame
         
        return self.resize_frame_with_border(self.frame)
        
    def resize_frame_with_border(self, frame):
        """
        Expecting 300x300 frame from oak, return size (450, 800)
        """
        # upscale image from (300,300) to (450,450)
        frame = cv2.resize(frame, (450,450), interpolation = cv2.INTER_AREA)
            
        # add left and right border to image of 175 pixels for total size (450, 800)
        frame = cv2.copyMakeBorder(src = frame, top = 0, bottom = 0, 
                                                left = 175, right = 175,
                                                borderType = cv2.BORDER_CONSTANT, value = (0,0,0))
        return frame

    def define_pipeline(self):
    
        # Start defining a pipeline
        pipeline = dai.Pipeline()

        # Define a source - color camera
        cam = pipeline.createColorCamera()
        cam.setPreviewSize(300, 300)
        cam.setInterleaved(False)

        # Define a neural network that will make predictions based on the source frames
        # DetectionNetwork class produces ImgDetections message that carries parsed
        # detection results.
        nn = pipeline.createMobileNetDetectionNetwork()
        nn.setBlobPath(self.nnPath)

        nn.setConfidenceThreshold(0.7)
        nn.setNumInferenceThreads(2)
        nn.input.setBlocking(False)

        cam.preview.link(nn.input)

        # Create XlinkOut nodes
        xoutFrame = pipeline.createXLinkOut()
        xoutFrame.setStreamName("rgb")
        cam.preview.link(xoutFrame.input)

        xoutNN = pipeline.createXLinkOut()
        xoutNN.setStreamName("nn")
        nn.out.link(xoutNN.input)
        
        return pipeline

    def start_pipeline(self):
        print("[INFO] Starting OAK Pipeline...")
        # Start pipeline
        self.device.startPipeline()

        # Output queues will be used to get the rgb frames and nn data from the
        # output streams defined above.
        qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)
            
        return (qRgb, qDet)
            
    def inference(self, show_display = False):
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()

        if inRgb is not None:
            self.frame = inRgb.getCvFrame()

        if inDet is not None:
            self.detections = inDet.detections
            self.counter += 1

        print(f"INFERENCE {self.counter}")
        return self.frame
          
    def __iter__(self):
        """
            Overwrites the default iter function so that you can iterate through this camera.
        """
        return OakIterator(self)


    def set_roi_coordinates(self, coordinates):
        """
            Updates Region of Interest(ROI) with the coordinates specified from the frontend.
        """
        self.ROI = coordinates
        
        
    def identify_stream_dimensions(self):
        """
            Get the dimensions of the frame to send to frontend.
        """

        # Set the width and height.
        frame = self.get_frame()            
        self.dimensions = frame.shape
        fe_height, fe_width, _ = (450, 800, 3)
        cam_height, cam_width, _ = self.dimensions
        
        self.frontend_ratio = [cam_width/fe_width, cam_height/fe_height]


class OakProcessing:
    """
        This object will determine if the ROI and detections match
        This object will also draw artifacts on frame
    """
    def __init__(self):
        self.frame = None
        self.ROI = []
        self.detections = None
        self.car_count = 0
        self.debugFrame = None
        self.counter = 0
        self.startTime = 0
        self.labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", 
                    "bottle", "bus", "car", "cat", "chair", "cow", \
                    "diningtable", "dog", "horse", "motorbike", "person", \
                    "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
    
    def set_frame_and_roi(self, frame, camera):
        """
            Empty function
        """
        self.frame = frame
        self.detections = camera.detections
        self.ROI = camera.ROI
        self.counter = camera.counter
        self.startTime = camera.startTime
    
    def detect_intersections(self, show_display = False):
        """
            Returns Debug Frame and Number of Detections in ROI
        """
        time.sleep(0.01)
        print(f"DETECT {self.counter}")

        self.debugFrame = self.processFrame(self.frame.copy())
        
        if show_display:
            cv2.imshow("rgb", self.debugFrame)
        
        return self.car_count, self.debugFrame    
        
    def processFrame(self, frame):

        frame = self.processFrameBBOX(frame)
        frame = self.resize_frame_with_border(frame)
        frame = self.processFrameROI(frame)
        frame = self.processFrameText(frame)
        
        return frame

    def processFrameBBOX(self, frame):
        car_count = 0
        
        for detection in self.detections:
            bbox_color = (0,0,255) # red
            
            # address bbox with correct label
            if self.labelMap[detection.label] in ["car", "motorbike", "person"]:
                bbox = self.frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))        
                
                if self.bbox_in_roi(bbox):
                    bbox_color = (0,255,0) # green
                    car_count += 1
                
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), bbox_color, 2)
                cv2.putText(frame, self.labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), \
                    cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), \
                    cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
        
        self.car_count = car_count
        
        return frame
        
    def processFrameROI(self, frame):
        # draw ROI
        cv2.polylines(frame, [np.asarray(self.ROI, np.int32).reshape((-1,1,2))], True, (255,255,255), 2)
        
        return frame

    def processFrameText(self, frame):
        # add text
        cv2.putText(frame, text=f"DETECTION", 
					org=(int(frame.shape[1]*0.008), int(frame.shape[0]*0.1)), 
					fontFace=cv2.FONT_HERSHEY_SIMPLEX, 
					fontScale=1, color=(255,255,255), thickness=2, lineType=cv2.LINE_AA)
        
        # show NN FPS
        cv2.putText(frame, text="NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
					org=(int(frame.shape[1]*0.008), int(frame.shape[0]*0.2)), 
					fontFace=cv2.FONT_HERSHEY_SIMPLEX, 
					fontScale=0.7, color=(255,255,255), thickness=2, lineType=cv2.LINE_AA)

        return frame

    # nn data (bounding box locations) are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)
        
    def bbox_in_roi(self, bbox):
        """
        Transform BBOX to match ROI frame size and check if BBOX in ROI
        """
    
        # transform bbox to fit from (300x300) to (450, 800) frame size
        mod_bbox = np.array(bbox) * 1.5
        mod_bbox = [int(pt) for pt in mod_bbox]
        mod_bbox[0] = mod_bbox[0] + 175
        mod_bbox[2] = mod_bbox[2] + 175
        pt_mod_bbox = [ [mod_bbox[0], mod_bbox[1]], 
                        [mod_bbox[2], mod_bbox[1]],
                        [mod_bbox[2], mod_bbox[3]],
                        [mod_bbox[0], mod_bbox[3]] 
                      ]
                      
        return intersection_of_polygons(self.ROI, pt_mod_bbox) 

    def resize_frame_with_border(self, frame):
        """
        Expecting 300x300 frame from oak, return size (450, 800)
        """
        frame = cv2.resize(frame, (450,450), interpolation = cv2.INTER_AREA)
        frame = cv2.copyMakeBorder(src = frame, top = 0, bottom = 0, 
                                                left = 175, right = 175,
                                                borderType = cv2.BORDER_CONSTANT, value = (0,0,0))
        return frame

class OakIterator:
    """
        This object is created so that you can iterate through a camera object
    """
    
    def __init__(self, camera):
        """
            Basic setup of iterator object.
        """
        self.camera = camera

    def __next__(self):
        """
            Allows iterating over this object to get each frame. Ex: "for frame in camera..."
        """        
        return self.camera.inference()

#### testing below ####
if __name__ == "__main__":

    camera1 = Oak()
    detection_algo = OakProcessing()

    while True:
        frame = camera1.inference()
        detection_algo.set_frame_and_roi(frame, camera1)
        detection_algo.detect_intersections(show_display = True)
        if cv2.waitKey(1) == ord('q'):
            break    
    

##################################
#    camera1 = Oak()
#
#    while True:
#        camera1.inference(show_display = True)
#    
#        if cv2.waitKey(1) == ord('q'):
#            break