#!/usr/bin/env python3

from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
import argparse
from time import monotonic

import shapely
from shapely.geometry import LineString, Point

nnPath    = str((Path(__file__).parent / Path('./models/OpenVINO_2021_2/mobilenet-ssd_openvino_2021.2_6shave.blob')).resolve().absolute())
videoPath = str((Path(__file__).parent / Path('./videos/video123-small.mp4')).resolve().absolute())

# MobilenetSSD label texts
labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

parser = argparse.ArgumentParser()
parser.add_argument('-cam', '--camera', action="store_true", help="Use DepthAI 4K RGB camera for inference (conflicts with -vid)")
parser.add_argument('-vid', '--video', type=str, help="Path to video file to be used for inference (conflicts with -cam)", default=videoPath)
args = parser.parse_args()

video = not args.camera

# Start defining a pipeline
pipeline = dai.Pipeline()

# Define a neural network that will make predictions based on the source frames
# DetectionNetwork class produces ImgDetections message that carries parsed
# detection results.
nn = pipeline.createMobileNetDetectionNetwork()
nn.setBlobPath(nnPath)

nn.setConfidenceThreshold(0.7)
nn.setNumInferenceThreads(2)
nn.input.setBlocking(False)

# Define a source for the neural network input
if video:
    # Create XLinkIn object as conduit for sending input video file frames
    # to the neural network
    xinFrame = pipeline.createXLinkIn()
    xinFrame.setStreamName("inFrame")
    # Connect (link) the video stream from the input queue to the
    # neural network input
    xinFrame.out.link(nn.input)
else:
    # Create color camera node.
    cam = pipeline.createColorCamera()
    cam.setPreviewSize(300, 300)
    cam.setInterleaved(False)
    # Connect (link) the camera preview output to the neural network input
    cam.preview.link(nn.input)

    # Create XLinkOut object as conduit for passing camera frames to the host
    xoutFrame = pipeline.createXLinkOut()
    xoutFrame.setStreamName("outFrame")
    cam.preview.link(xoutFrame.input)

# Create neural network output (inference) stream
nnOut = pipeline.createXLinkOut()
nnOut.setStreamName("nn")
nn.out.link(nnOut.input)

# Pipeline defined, now the device is connected to
with dai.Device(pipeline) as device:

    # Start pipeline
    device.startPipeline()

    # Define queues for image frames
    if video:
        # Input queue for sending video frames to device
        qIn_Frame = device.getInputQueue(name="inFrame", maxSize=4, blocking=False)
    else:
        # Output queue for retrieving camera frames from device
        qOut_Frame = device.getOutputQueue(name="outFrame", maxSize=4, blocking=False)

    qDet = device.getOutputQueue(name="nn", maxSize=4, blocking=False)

    if video:
        cap = cv2.VideoCapture(videoPath)
    
    def should_run():
        return cap.isOpened() if video else True

    def get_frame():
        if video:
            return cap.read()
        else:
            in_Frame= qOut_Frame.get()
            frame = in_Frame.getCvFrame()
            return True, frame

    startTime = time.monotonic()
    counter = 0
    detections = []
    frame = None

    # nn data (bounding box locations) are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def to_planar(arr: np.ndarray, shape: tuple) -> np.ndarray:
            return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()
            
    def is_intersection(roi_line, bbox):
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
    
    def displayFrame(name, frame):
        roi_line = [(int(frame.shape[1]/2), 0), (int(frame.shape[1]/2), frame.shape[0])]
        cv2.line(frame, roi_line[0], roi_line[1], (255,0,0), 2)
        cv2.putText(frame, "NN fps: {:.2f}".format(counter / (time.monotonic() - startTime)),
                                (2, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color=(255, 255, 0))
        
        for detection in detections:
            bbox_color = (0,0,255)
            
            if labelMap[detection.label] in ["car", "motorbike", "person"]:
                bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))

                in_roi = is_intersection(roi_line, bbox)
                
                if in_roi:
                    bbox_color = (0,255,0)
                
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), bbox_color, 2)
                cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, bbox_color)
                print(f"{(bbox[0], bbox[1]), (bbox[2], bbox[3])} {labelMap[detection.label]}")
        
        cv2.imshow(name, frame)
        

    while should_run():
        # Get image frames from camera or video file
        read_correctly, frame = get_frame()
        if not read_correctly:
            break

        if video:
            #frame = cv2.resize(frame, (0, 0), fx = 0.4, fy = 0.4) 
            # Prepare image frame from video for sending to device
            img = dai.ImgFrame()
            img.setData(to_planar(frame, (300, 300)))
            img.setTimestamp(monotonic())
            img.setWidth(300)
            img.setHeight(300)
            
            # Use input queue to send video frame to device
            qIn_Frame.send(img)
        else:
            in_Frame = qOut_Frame.tryGet()

            if in_Frame is not None:
                frame = in_Frame.getCvFrame()

        inDet = qDet.tryGet()
        if inDet is not None:
            detections = inDet.detections
            counter += 1

            # if the frame is available, render detection data on frame and display.
        if frame is not None:
            displayFrame("", frame)

        if cv2.waitKey(1) == ord('q'):
            break

        

