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
        self.ROI = None
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
        
        self.frame = None
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
            return inRgb.getCvFrame()
         
        return self.frame
    
    def get_debug_frame(self):
        return self.debugFrame

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
            
    def inference(self):
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()

        if inRgb is not None:
            self.frame = inRgb.getCvFrame()

        if inDet is not None:
            self.detections = inDet.detections
            self.counter += 1

        # if the frame is available, render detection data on frame and display.
        if self.frame is not None:
            self.displayFrame("rgb", self.frame)
        
        return (self.frame, self.debugFrame)

    # nn data (bounding box locations) are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def displayFrame(self, name, frame):
        cv2.putText(self.frame, "NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
                (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color=(255, 255, 255))
        
        for detection in self.detections:
            bbox = self.frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
            cv2.putText(frame, self.labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), \
                cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), \
                cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
        
        self.debugFrame = frame
        cv2.imshow(name, frame)

    def detect_intersections(self):
        pass
          
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
        while frame is None:
            frame = self.get_frame()
            time.sleep(0.01)
            
        self.dimensions = frame.shape
        print(f"[INFO] OAK Dimensions: {self.dimensions}")
        self.prepare_ratio = [800/self.dimensions[0],1]
        self.frontend_ratio = [450/(self.dimensions[0]*self.prepare_ratio[0]),800/(self.dimensions[1]*self.prepare_ratio[1])]

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
        frame = self.camera.get_frame()
        while frame is None:
            frame = self.camera.get_frame()
            time.sleep(0.01)
        
        return frame

#### testing below ####
if __name__ == "__main__":
    camera1 = Oak()

    while True:
        camera1.inference()
    
        if cv2.waitKey(1) == ord('q'):
            break