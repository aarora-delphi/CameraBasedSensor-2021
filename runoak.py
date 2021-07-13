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
        self.ROI = [[50, 50], [250, 50], [250, 250], [50, 250]] # sample ROI
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
            
    def define_pipeline(self):
    
        # Start defining a pipeline
        pipeline = dai.Pipeline()

        # Define a source - color camera
        cam = pipeline.createColorCamera()
        cam.setPreviewKeepAspectRatio(True)
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
    
    def detect_intersections(self, show_display = False):
        """
            Returns Debug Frame and Number of Detections in ROI
        """
        print(f"DETECT {self.counter}")

        self.processFrame()
        
        if show_display:
            cv2.imshow("rgb", self.debugFrame)
        
        return self.car_count, self.debugFrame    
        
    def processFrame(self):
    
        frame = self.frame.copy()
        frame = self.processFrameBBOX(frame)
        frame = self.processFrameROI(frame)
        frame = self.processFrameText(frame)
        
        self.debugFrame = frame

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
		# show NN FPS
        cv2.putText(frame, "NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
                                (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color=(255, 255, 255))

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
        mod_bbox = bbox
        pt_mod_bbox = [ [mod_bbox[0], mod_bbox[1]], 
                        [mod_bbox[2], mod_bbox[1]],
                        [mod_bbox[2], mod_bbox[3]],
                        [mod_bbox[0], mod_bbox[3]] 
                      ]
                      
        return intersection_of_polygons(self.ROI, pt_mod_bbox) 

#### testing below ####
if __name__ == "__main__":

    camera1 = Oak()

    while True:
        camera1.inference()
        camera1.detect_intersections(show_display = True)
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