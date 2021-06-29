### Trash File Later - 6/29/2021 - use oak.py instead - this is just a pathfinder

from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
import argparse
from time import monotonic

import shapely
from shapely.geometry import LineString, Point

class Oak():
    def __init__(self, video = False):
        self.video = video
        self.nnPath = str((Path(__file__).parent / Path('./OAK_Course_Examples/models/OpenVINO_2021_2/mobilenet-ssd_openvino_2021.2_6shave.blob')).resolve().absolute())
        self.videoPath = str((Path(__file__).parent / Path('./OAK_Course_Examples/videos/video123.mp4')).resolve().absolute())
        
        # MobilenetSSD label texts
        self.labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
            
        # Start defining a pipeline
        self.pipeline = dai.Pipeline()

        # Define a neural network that will make predictions based on the source frames
        # DetectionNetwork class produces ImgDetections message that carries parsed
        # detection results.
        self.nn = self.pipeline.createMobileNetDetectionNetwork()
        self.nn.setBlobPath(self.nnPath)

        self.nn.setConfidenceThreshold(0.7)
        self.nn.setNumInferenceThreads(2)
        self.nn.input.setBlocking(False)
        
        # Define a source for the neural network input
        if self.video:
            # Create XLinkIn object as conduit for sending input video file frames
            # to the neural network
            self.xinFrame = self.pipeline.createXLinkIn()
            self.xinFrame.setStreamName("inFrame")
            # Connect (link) the video stream from the input queue to the
            # neural network input
            self.xinFrame.out.link(self.nn.input)
        else:
            # Create color camera node.
            self.cam = pipeline.createColorCamera()
            self.cam.setPreviewSize(300, 300)
            self.cam.setInterleaved(False)
            # Connect (link) the camera preview output to the neural network input
            self.cam.preview.link(self.nn.input)

            # Create XLinkOut object as conduit for passing camera frames to the host
            self.xoutFrame = pipeline.createXLinkOut()
            self.xoutFrame.setStreamName("outFrame")
            self.cam.preview.link(self.xoutFrame.input)

        # Create neural network output (inference) stream
        self.nnOut = self.pipeline.createXLinkOut()
        self.nnOut.setStreamName("nn")
        self.nn.out.link(self.nnOut.input)
        
        # Pipeline defined, now the device is connected to
        with dai.Device(self.pipeline) as self.device:

            # Start pipeline
            self.device.startPipeline()

            # Define queues for image frames
            if self.video:
                # Input queue for sending video frames to device
                self.qIn_Frame = self.device.getInputQueue(name="inFrame", maxSize=4, blocking=False)
            else:
                # Output queue for retrieving camera frames from device
                self.qOut_Frame = self.device.getOutputQueue(name="outFrame", maxSize=4, blocking=False)

            self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)

            if self.video:
                self.cap = cv2.VideoCapture(self.videoPath)
                
            self.startTime = time.monotonic()
            self.counter = 0
            self.detections = []
            self.frame = None
    
    def inference(self):
        # Get image frames from camera or video file
        
        read_correctly, self.frame = self.get_frame()
        if not read_correctly:
            return

        if self.video:
            
            # Prepare image frame from video for sending to device
            img = dai.ImgFrame()
            img.setData(self.to_planar(self.frame, (300, 300)))
            img.setTimestamp(monotonic())
            img.setWidth(300)
            img.setHeight(300)
            
            # Use input queue to send video frame to device
            self.qIn_Frame.send(img)
        else:
            in_Frame = self.qOut_Frame.tryGet()

            if in_Frame is not None:
                self.frame = in_Frame.getCvFrame()

        inDet = self.qDet.tryGet()
        if inDet is not None:
            self.detections = inDet.detections
            counter += 1

            # if the frame is available, render detection data on frame and display.
        if self.frame is not None:
            self.displayFrame("", self.frame, self.detections)

        if cv2.waitKey(1) == ord('q'):
            return

    def should_run(self):
        return self.cap.isOpened() if self.video else True

    def get_frame(self):
        if self.video:
            return self.cap.read()
        else:
            self.in_Frame= self.qOut_Frame.get()
            self.frame = self.in_Frame.getCvFrame()
            return True, self.frame

    # nn data (bounding box locations) are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def to_planar(self, arr: np.ndarray, shape: tuple) -> np.ndarray:
            return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()
            
    def is_intersection(self, roi_line, bbox):
        roi_line_shapely = LineString(roi_line)
        
        # roi intersects bbox
        top_line = LineString([(bbox[0],bbox[1]), (bbox[2], bbox[1])])
        bot_line = LineString([(bbox[2],bbox[3]), (bbox[0], bbox[3])])
        ###lft_line = LineString([(bbox[0],bbox[3]), (bbox[0], bbox[1])])
        ###rgt_line = LineString([(bbox[2],bbox[1]), (bbox[2], bbox[3])])

        top_pt = str(roi_line_shapely.intersection(top_line)) != "LINESTRING EMPTY"
        bot_pt = str(roi_line_shapely.intersection(bot_line)) != "LINESTRING EMPTY"
        ###lft_pt = str(roi_line_shapely.intersection(lft_line)) != "LINESTRING EMPTY"
        ###rgt_pt = str(roi_line_shapely.intersection(rgt_line)) != "LINESTRING EMPTY"
        
        # roi within bbox
        int_pt1 = (bbox[0] <= roi_line[0][0] <= bbox[2]) and (bbox[1] <= roi_line[0][1] <= bbox[3])
        int_pt2 = (bbox[0] <= roi_line[1][0] <= bbox[2]) and (bbox[1] <= roi_line[1][1] <= bbox[3])
        
        return top_pt or bot_pt or (int_pt1 and int_pt2) ### or lft_pt or rgt_pt
    
    def displayFrame(self, name, frame, detections):
        roi_line = [(int(frame.shape[1]/2), 0), (int(frame.shape[1]/2), frame.shape[0])]
        cv2.line(frame, roi_line[0], roi_line[1], (255,0,0), 2)
        cv2.putText(frame, "NN fps: {:.2f}".format(counter / (time.monotonic() - startTime)),
                                (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color=(255, 255, 0))
        
        for detection in detections:
            bbox_color = (0,0,255)
            
            if labelMap[detection.label] in ["car", "motorbike"]:
                bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))

                in_roi = is_intersection(roi_line, bbox)
                
                if in_roi:
                    bbox_color = (0,255,0)
                
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), bbox_color, 2)
                cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
                print(f"{(bbox[0], bbox[1]), (bbox[2], bbox[3])} {labelMap[detection.label]}")
        cv2.imshow(name, frame)
        
        
if __name__ == "__main__":
    camera1 = Oak(video=True)
    
    while camera1.should_run():
        camera1.inference()
        

            
        
        
        
        