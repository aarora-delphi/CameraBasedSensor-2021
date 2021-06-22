#!/usr/bin/env python3

from pathlib import Path
import sys
import cv2
import depthai as dai
import numpy as np
import time
# Plot values in opencv program

# Plot values in opencv program (source: https://github.com/2vin/opencv-plot)
class Plotter:
    def __init__(self, plot_width, plot_height,sample_buffer=None):
        self.width = plot_width
        self.height = plot_height
        self.color = (0, 255 ,0)
        self.plot_canvas = np.ones((self.height, self.width, 3))*255
        self.ltime = 0
        self.plots = {}
        self.plot_t_last = {}
        self.margin_l = 40
        self.margin_r = 20
        self.margin_u = 20
        self.margin_d = 50
        self.sample_buffer = self.width if sample_buffer is None else sample_buffer

    # Update new values in plot
    def plot(self, val, label = "plot"):
        if not label in self.plots:
            self.plots[label] = []
            self.plot_t_last[label] = 0

        self.plots[label].append(int(val))
        while len(self.plots[label]) > self.sample_buffer:
            self.plots[label].pop(0)
            self.show_plot(label)
            # Show plot using opencv imshow
    def show_plot(self, label):

        self.plot_canvas = np.zeros((self.height, self.width, 3))

        # Specific vertical scaling to achieve a plot upper limit of 2 meters for
        # the y-axis. This assumes a frame height of 400 pixels.
        scale_h = 2*(self.height-self.margin_d-self.margin_u)/self.height
        # Use the line below to achieve a plot upper limit of 4 meters for
        # the y-axis. This assumes a frame height of 400 pixels.
        #scale_h = (self.height-self.margin_d-self.margin_u)/self.height

        # Draw grid lines
        cv2.line(self.plot_canvas, (self.margin_l, int((self.height-self.margin_d-self.margin_u)/4)+self.margin_u ), (self.width-self.margin_r, int((self.height-self.margin_d-self.margin_u)/4)+self.margin_u), (1,1,1), 1)
        cv2.line(self.plot_canvas, (self.margin_l, int((self.height-self.margin_d-self.margin_u)/2)+self.margin_u ), (self.width-self.margin_r, int((self.height-self.margin_d-self.margin_u)/2)+self.margin_u), (1,1,1), 1)
        cv2.line(self.plot_canvas, (self.margin_l, int((self.height-self.margin_d-self.margin_u)*3/4)+self.margin_u ), (self.width-self.margin_r, int((self.height-self.margin_d-self.margin_u)*3/4)+self.margin_u), (1,1,1), 1, )

        color = (255,255,255)
        for j,i in enumerate(np.linspace(0,self.sample_buffer-2,self.width-self.margin_l-self.margin_r)):
            i = int(i)
            cv2.line(self.plot_canvas, (j+self.margin_l, int((self.height-self.margin_d-self.margin_u) +self.margin_u- self.plots[label][i]*scale_h)), (j+self.margin_l, int((self.height-self.margin_d-self.margin_u)  +self.margin_u- self.plots[label][i+1]*scale_h)), self.color, 1)

        # Draw plot border
        cv2.rectangle(self.plot_canvas, (self.margin_l,self.margin_u), (self.width-self.margin_r,self.height-self.margin_d), color, 1)

        # Add y-axis gridline values
        fontType = cv2.FONT_HERSHEY_TRIPLEX
        font_adjust = 5
        cv2.putText(self.plot_canvas,f"{200}", (int(font_adjust),int(0)+self.margin_u + font_adjust), fontType,0.5,color)
        cv2.putText(self.plot_canvas,f"{150}", (int(font_adjust),int((self.height-self.margin_d-self.margin_u)*1/4)+self.margin_u + font_adjust),fontType,0.5,color)
        cv2.putText(self.plot_canvas,f"{100}", (int(font_adjust),int((self.height-self.margin_d-self.margin_u)*1/2)+self.margin_u + font_adjust),fontType,0.5,color)
        cv2.putText(self.plot_canvas,f"{ 50}", (int(font_adjust+11),int((self.height-self.margin_d-self.margin_u)*3/4)+self.margin_u + font_adjust),fontType,0.5,color)
        cv2.putText(self.plot_canvas,f"{  0}", (int(font_adjust+21),int((self.height-self.margin_d-self.margin_u)*4/4)+self.margin_u + font_adjust),fontType,0.5,color)

        cv2.putText(self.plot_canvas,f" {label} : {self.plots[label][-1]}",(int(self.width/2 - 100),self.height-20),fontType,0.6,(0,255,255))

        self.plot_t_last[label] = time.time()
        cv2.imshow(label, self.plot_canvas)
        cv2.waitKey(1)

'''
Spatial detection network demo.
    Performs inference on RGB camera and retrieves spatial location coordinates: x,y,z relative to the center of depth map.
'''

# MobilenetSSD label texts
labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

syncNN = True

# Get argument first
nnBlobPath = str((Path(__file__).parent / Path('./models/OpenVINO_2021_2/mobilenet-ssd_openvino_2021.2_6shave.blob')).resolve().absolute())
if len(sys.argv) > 1:
    nnBlobPath = sys.argv[1]

# Start defining a pipeline
pipeline = dai.Pipeline()

#-------------------------------------------------------------------------------
# Define a source - two mono (grayscale) cameras for depth and rbg for preview.
#-------------------------------------------------------------------------------
monoLeft = pipeline.createMonoCamera()
monoRight = pipeline.createMonoCamera()

height = monoLeft.getResolutionHeight()
width = monoLeft.getResolutionWidth()

monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

colorCam = pipeline.createColorCamera()
colorCam.setPreviewSize(300, 300)
colorCam.setInterleaved(False)
colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)

#---------------------------------------------------------------------------
# Define stereoDepth and spatialDetectionNetwork nodes and create outputs.
#---------------------------------------------------------------------------
spatialDetectionNetwork = pipeline.createMobileNetSpatialDetectionNetwork()
stereo = pipeline.createStereoDepth()

stereo.setOutputDepth(True)

xoutRgb = pipeline.createXLinkOut()
xoutNN = pipeline.createXLinkOut()
xoutBoundingBoxDepthMapping = pipeline.createXLinkOut()
xoutDepth = pipeline.createXLinkOut()

xoutRgb.setStreamName("rgb")
xoutNN.setStreamName("detections")
xoutBoundingBoxDepthMapping.setStreamName("boundingBoxDepthMapping")
xoutDepth.setStreamName("depth")

#---------------------------------------------------------------------------
# Configure spatialDetectionNetwork.
#---------------------------------------------------------------------------
spatialDetectionNetwork.setBlobPath(nnBlobPath)
spatialDetectionNetwork.setConfidenceThreshold(0.7)
spatialDetectionNetwork.setBoundingBoxScaleFactor(1.0)
spatialDetectionNetwork.setDepthLowerThreshold(100)
spatialDetectionNetwork.setDepthUpperThreshold(5000)

#------------------------------------
# Define connectivity between nodes.
#------------------------------------
monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)
colorCam.preview.link(spatialDetectionNetwork.input)
if(syncNN):
    spatialDetectionNetwork.passthrough.link(xoutRgb.input)
else:
    colorCam.preview.link(xoutRgb.input)

spatialDetectionNetwork.out.link(xoutNN.input)
spatialDetectionNetwork.boundingBoxMapping.link(xoutBoundingBoxDepthMapping.input)

stereo.depth.link(spatialDetectionNetwork.inputDepth)
spatialDetectionNetwork.passthroughDepth.link(xoutDepth.input)

# Pipeline defined, now the device is connected to
with dai.Device(pipeline) as device:
    # Start pipeline
    device.startPipeline()

    # Output queues will be used to get the rgb frames and nn data from the outputs defined above
    previewQueue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
    detectionNNQueue = device.getOutputQueue(name="detections", maxSize=4, blocking=False)
    xoutBoundingBoxDepthMapping = device.getOutputQueue(name="boundingBoxDepthMapping", maxSize=4, blocking=False)
    depthQueue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)

    frame = None
    detections = []

    startTime = time.monotonic()
    counter = 0
    fps = 0
    color = (255, 255, 255)

    # Create real-time plotter object.
    p = Plotter(640, 400, sample_buffer=100)

    while True:
        inPreview = previewQueue.get()
        inNN = detectionNNQueue.get()
        depth = depthQueue.get()

        counter+=1
        current_time = time.monotonic()
        if (current_time - startTime) > 1 :
            fps = counter / (current_time - startTime)
            counter = 0
            startTime = current_time

        frame = inPreview.getCvFrame()
        depthFrame = depth.getFrame()

        depthFrameColor = cv2.normalize(depthFrame, None, 255, 0, cv2.NORM_INF, cv2.CV_8UC1)
        depthFrameColor = cv2.equalizeHist(depthFrameColor)
        depthFrameColor = cv2.applyColorMap(depthFrameColor, cv2.COLORMAP_HOT)
        detections = inNN.detections
        if len(detections) != 0:
            boundingBoxMapping = xoutBoundingBoxDepthMapping.get()
            roiDatas = boundingBoxMapping.getConfigData()

            for roiData in roiDatas:
                roi = roiData.roi
                roi = roi.denormalize(depthFrameColor.shape[1], depthFrameColor.shape[0])
                topLeft = roi.topLeft()
                bottomRight = roi.bottomRight()
                xmin = int(topLeft.x)
                ymin = int(topLeft.y)
                xmax = int(bottomRight.x)
                ymax = int(bottomRight.y)

                # Annotate depth frame with scaled bounding box.
                fontType = cv2.FONT_HERSHEY_TRIPLEX
                cv2.rectangle(depthFrameColor, (xmin, ymin), (xmax, ymax), color, 2)

        # if the frame is available, draw bounding boxes on it and show the frame
        height = frame.shape[0]
        width  = frame.shape[1]
        for detection in detections:
            # denormalize bounding box
            x1 = int(detection.xmin * width)
            x2 = int(detection.xmax * width)
            y1 = int(detection.ymin * height)
            y2 = int(detection.ymax * height)
            try:
                label = labelMap[detection.label]
            except:
                label = detection.label

            z_cm = int(detection.spatialCoordinates.z/10)

            cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, "{:.2f}".format(detection.confidence*100), (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, f"X: {int(detection.spatialCoordinates.x)} mm", (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, f"Y: {int(detection.spatialCoordinates.y)} mm", (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, f"Z: {int(detection.spatialCoordinates.z)} mm", (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

            # Annotate depth frame
            cv2.putText(depthFrameColor, f"{z_cm}", (int(xmin+(xmax-xmin)/2-15), int(ymin+(ymax-ymin)/2)), fontType, .6, color)
            cv2.putText(depthFrameColor, f"cm",     (int(xmin+(xmax-xmin)/2-12), int(ymin+(ymax-ymin)/2 + 15)), fontType, 0.6, color)

        cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)
        cv2.imshow("depth", depthFrameColor)
        cv2.imshow("rgb", frame)

        if len(detections) != 0:
            p.plot(z_cm, label='Distance [cm]')

        if cv2.waitKey(1) == ord('q'):
            break
