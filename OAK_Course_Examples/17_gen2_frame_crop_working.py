#!/usr/bin/env python3

from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-video', '--video', action="store_true", help="Save a video of the recording")
args = parser.parse_args()

nnPath = str((Path(__file__).parent / Path('./models/OpenVINO_2021_2/mobilenet-ssd_openvino_2021.2_6shave.blob')).resolve().absolute())

# MobilenetSSD class labels
labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

# Start defining a pipeline
pipeline = dai.Pipeline()

# Define a source - color camera
cam = pipeline.createColorCamera()
cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
cam.setPreviewSize(1920, 1080)
cam.setInterleaved(False)

nn = pipeline.createMobileNetDetectionNetwork()
nn.setBlobPath(nnPath)
nn.setConfidenceThreshold(0.7)
nn.setNumInferenceThreads(2)
nn.input.setBlocking(False)

def square_crop(crop, frame_size = (1920, 1080)):
    width, height = frame_size 
    
    xmin = crop[0] * width
    ymin = crop[1] * height
    xmax = crop[2] * width
    ymax = crop[3] * height

    diffx = xmax - xmin
    diffy = ymax - ymin
    
    shift = abs(diffx - diffy) / 2
    
    if diffy > diffx:
        xmin -= shift
        xmax += shift
    else:
        ymin -= shift
        ymax += shift
    
    if xmin < 0:
        xmax += abs(xmin)
        xmin = 0
    if xmax > width:
        xmin -= (xmax - width)
        xmax = width
    if ymin < 0:
        ymax += abs(ymin)
        ymin = 0
    if ymax > height:
        ymin -= (ymax - height)
        ymax = height
    
    return (xmin / width, ymin / height, xmax / width, ymax / height)

pick_crop = (0.05, 0.2, 0.8, 0.6) # (xmin, ymin, xmax, ymax)
set_crop = square_crop(pick_crop) # if negative val in set crop - crop from center of ROI full frame # TO DO

print(f"[INFO] Pick Crop - {pick_crop}")
print(f"[INFO] Set Crop - {set_crop}")

manip_crop = pipeline.create(dai.node.ImageManip)
manip_crop.initialConfig.setCropRect(set_crop[0], set_crop[1], set_crop[2], set_crop[3])
manip_crop.initialConfig.setResize(300, 300)
manip_crop.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)
cam.preview.link(manip_crop.inputImage)

manip_view = pipeline.create(dai.node.ImageManip)
manip_view.initialConfig.setResize(640, 360)
manip_view.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)
cam.preview.link(manip_view.inputImage)

manip_crop.out.link(nn.input)

# Create XlinkOut nodes
xoutFrame = pipeline.createXLinkOut()
xoutFrame.setStreamName("rgb")
manip_crop.out.link(xoutFrame.input)

xoutVideo = pipeline.createXLinkOut() 
xoutVideo.setStreamName("video") 
manip_view.out.link(xoutVideo.input)

xoutNN = pipeline.createXLinkOut()
xoutNN.setStreamName("nn")
nn.out.link(xoutNN.input)


save_video = args.video

if save_video:
    size = (640, 360)
    deviceID = dai.Device.getAllAvailableDevices()[0].getMxId()
    vresult = cv2.VideoWriter(f"recording-{deviceID}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.mp4", cv2.VideoWriter_fourcc(*'mp4v'), 30, size)
    print("[INFO] Creating Video Object")
    print(f"[INFO] Recording Video of {deviceID}")

# Pipeline defined, now the device is connected to
with dai.Device(pipeline) as device:

    # Start pipeline
    device.startPipeline()
    qRgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
    qVideo = device.getOutputQueue(name="video", maxSize=4, blocking=False)
    qDet = device.getOutputQueue(name="nn", maxSize=4, blocking=False)
    
    startTime = time.monotonic()
    counter = 0
    detections = []
    frame = None

    # nn data (bounding box locations) are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def displayFrame(name, frame):
        for detection in detections:
            if labelMap[detection.label] in ["bus", "car", "motorbike", "person"]:
                bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
                cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
        
        cv2.putText(frame, "NN fps: {:.2f}".format(counter / (time.monotonic() - startTime)),
                        (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color=(255, 255, 255))
        
        cv2.imshow(name, frame)

    def videoNorm(start, height, width, bbox):
        normVals = np.full(len(bbox), height)
        normVals[::2] = width
        point = (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)
        norm = (point[0] + start[0], 
                point[1] + start[1], 
                point[2] + start[0], 
                point[3] + start[1])
        return norm
        
    def displayVideo(name, frame):
        orig_crop = videoNorm((0,0), frame.shape[0], frame.shape[1], pick_crop)
        crop = videoNorm((0,0), frame.shape[0], frame.shape[1], set_crop)
        
        for detection in detections:
            if labelMap[detection.label] in ["bus", "car", "motorbike", "person"]:
                set_detect = (detection.xmin, detection.ymin, detection.xmax, detection.ymax)
                bbox = videoNorm((crop[0], crop[1]), crop[3]-crop[1], crop[2]-crop[0], set_detect)
                
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
                cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
        
        cv2.rectangle(frame, (crop[0], crop[1]), (crop[2], crop[3]), (255, 255, 0), 2)
        cv2.rectangle(frame, (orig_crop[0], orig_crop[1]), (orig_crop[2], orig_crop[3]), (255, 0, 255), 2)
        
        cv2.putText(frame, "NN fps: {:.2f}".format(counter / (time.monotonic() - startTime)),
                        (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color=(255, 255, 255))
        
        cv2.imshow(name, frame)


    frame = None
    vframe = None

    while True:
        try:
            inRgb = qRgb.tryGet()
            inVideo = qVideo.tryGet() 
            inDet = qDet.tryGet()

            if inRgb is not None:
                frame = inRgb.getCvFrame()
            
            if inVideo is not None: 
                vframe = inVideo.getCvFrame()
            
            if inDet is not None:
                detections = inDet.detections
                counter += 1

            # if the frame is available, render detection data on frame and display.
            if frame is not None:
                displayFrame("rgb", frame)

            if vframe is not None: 
                #cv2.imshow("video", vframe)
                displayVideo("video", vframe)
            
                if save_video:
                    vresult.write(vframe)

            if cv2.waitKey(1) == ord('q'):
                break
        
        except KeyboardInterrupt:
            print(f"[INFO] Keyboard Interrupt")
            break

if save_video:
    vresult.release()
    print("[INFO] Released Video Write Object")