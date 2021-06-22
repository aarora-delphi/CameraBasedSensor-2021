#!/usr/bin/env python3
import cv2
import depthai as dai
import numpy as np
import time

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
        color = (255,255,255)
        for j,i in enumerate(np.linspace(0,self.sample_buffer-2,self.width-self.margin_l-self.margin_r)):
            i = int(i)
            cv2.line(self.plot_canvas, (j+self.margin_l, int((self.height-self.margin_d-self.margin_u) +self.margin_u- self.plots[label][i]*scale_h)), (j+self.margin_l, int((self.height-self.margin_d-self.margin_u)  +self.margin_u- self.plots[label][i+1]*scale_h)), self.color, 1)

        # Draw plot border
        cv2.rectangle(self.plot_canvas, (self.margin_l,self.margin_u), (self.width-self.margin_r,self.height-self.margin_d), color, 1)
        # Draw grid lines
        cv2.line(self.plot_canvas, (self.margin_l, int((self.height-self.margin_d-self.margin_u)/4)+self.margin_u ), (self.width-self.margin_r, int((self.height-self.margin_d-self.margin_u)/4)+self.margin_u), (1,1,1), 1)
        cv2.line(self.plot_canvas, (self.margin_l, int((self.height-self.margin_d-self.margin_u)/2)+self.margin_u ), (self.width-self.margin_r, int((self.height-self.margin_d-self.margin_u)/2)+self.margin_u), (1,1,1), 1)
        cv2.line(self.plot_canvas, (self.margin_l, int((self.height-self.margin_d-self.margin_u)*3/4)+self.margin_u ), (self.width-self.margin_r, int((self.height-self.margin_d-self.margin_u)*3/4)+self.margin_u), (1,1,1), 1, )

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

# Start defining a pipeline.
pipeline = dai.Pipeline()

#-------------------------------------------------------------------------------
# Define a source - two mono (grayscale) cameras for depth and rbg for preview.
#-------------------------------------------------------------------------------
monoLeft = pipeline.createMonoCamera()
monoRight = pipeline.createMonoCamera()

monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

height = monoLeft.getResolutionHeight()
width = monoLeft.getResolutionWidth()

colorCam = pipeline.createColorCamera()
colorCam.setPreviewSize(300, 300)
colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
colorCam.setInterleaved(False)
colorCam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

#---------------------------------------------------------------------------
# Define stereoDepth and spatialLocationCalculator nodes and create outputs.
#---------------------------------------------------------------------------
stereo = pipeline.createStereoDepth()
spatialLocationCalculator = pipeline.createSpatialLocationCalculator()

# Set StereoDepth configurations
stereo.setOutputDepth(True)

xoutRgb = pipeline.createXLinkOut()
xoutDepth = pipeline.createXLinkOut()
xoutSpatialData = pipeline.createXLinkOut()

xoutRgb.setStreamName("rgb")
xoutDepth.setStreamName("depth")
xoutSpatialData.setStreamName("spatialData")

#----------------------------------------------------------------------------
# Create an input for configuring the spatialLocationCalculator in realtime.
#----------------------------------------------------------------------------
xinSpatialCalcConfig = pipeline.createXLinkIn()
xinSpatialCalcConfig.setStreamName("spatialCalcConfig")

#------------------------------------
# Define connectivity between nodes.
#------------------------------------
monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)
colorCam.preview.link(xoutRgb.input)
spatialLocationCalculator.passthroughDepth.link(xoutDepth.input)
stereo.depth.link(spatialLocationCalculator.inputDepth)
spatialLocationCalculator.out.link(xoutSpatialData.input)
xinSpatialCalcConfig.out.link(spatialLocationCalculator.inputConfig)

#----------------------------------------
# Set up initial ROI size and location.
#----------------------------------------
roi_size = 220
roi_x = int(width/2)
roi_y = int(height/2)
topLeft = dai.Point2f((roi_x-roi_size/2)/width, (roi_y-roi_size/2)/height)
bottomRight = dai.Point2f((roi_x+roi_size/2)/width, (roi_y+roi_size/2)/height)

#----------------------------
# Setup ROI configuration.
#----------------------------
config = dai.SpatialLocationCalculatorConfigData()
# Specify min/max threshold (in mm) for the depth calculation.
config.roi = dai.Rect(topLeft, bottomRight)
config.depthThresholds.lowerThreshold = 50
config.depthThresholds.upperThreshold = 5000
spatialLocationCalculator.initialConfig.addROI(config)

# Pixel step size for real-time ROI adjustment.
stepSize = 30

#---------------------------------------------------------------------------
# Pipeline defined, now the device is assigned and the pipeline is started.
#---------------------------------------------------------------------------
device = dai.Device(pipeline)
device.startPipeline()

#---------------------------
# Define the output queues.
#---------------------------
previewQueue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
depthQueue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
spatialCalcQueue = device.getOutputQueue(name="spatialData", maxSize=4, blocking=False)

#----------------------------------------------
# Define the input queue for updating the ROI.
#----------------------------------------------
spatialCalcConfigInQueue = device.getInputQueue("spatialCalcConfig")

color = (0, 255, 0)

# Create real-time plotter object.
p = Plotter(width, height, sample_buffer=200)

while True:
    inPreview = previewQueue.get()        # Preview frame (rgb)
    inDepth = depthQueue.get()            # Depth frame
    inDepthAvg = spatialCalcQueue.get()   # Spatial data

    rgbFrame = inPreview.getCvFrame()

    # Get the depth frame and post-process it for display.
    depthFrame = inDepth.getFrame()
    depthFrameColor = cv2.normalize(depthFrame, None, 255, 0, cv2.NORM_INF, cv2.CV_8UC1)
    depthFrameColor = cv2.equalizeHist(depthFrameColor)
    depthFrameColor = cv2.applyColorMap(depthFrameColor, cv2.COLORMAP_HOT)

    spatialData = inDepthAvg.getSpatialLocations()
    idx = 0
    for depthData in spatialData:
        roi = depthData.config.roi
        roi = roi.denormalize(width=depthFrameColor.shape[1], height=depthFrameColor.shape[0])
        xmin = int(roi.topLeft().x)
        ymin = int(roi.topLeft().y)
        xmax = int(roi.bottomRight().x)
        ymax = int(roi.bottomRight().y)

        z_cm = int(depthData.spatialCoordinates.z/10)
        idx += 1

        fontType = cv2.FONT_HERSHEY_TRIPLEX
        cv2.rectangle(depthFrameColor, (xmin, ymin), (xmax, ymax), color, thickness=2)
        cv2.putText(depthFrameColor, f"{z_cm}", (int(xmin+(xmax-xmin)/2-15), int(ymin+(ymax-ymin)/2)), fontType, .5, (0,0,0))
        cv2.putText(depthFrameColor, f"cm",     (int(xmin+(xmax-xmin)/2-13), int(ymin+(ymax-ymin)/2 + 15)), fontType, .5, (0,0,0))
    cv2.imshow("rgb", rgbFrame)
    cv2.imshow("depth", depthFrameColor)

    # Real time distance plot for ROI.
    p.plot(z_cm, label='Distance [cm]')

    newConfig = False
    key = cv2.waitKey(1)

    if key == ord('q'):
        break
    elif key == ord('s'):
        # Make thr ROI smaller (s)
        if bottomRight.y - topLeft.y - stepSize/width >= 0:
            topLeft.x += stepSize/width
            topLeft.y += stepSize/height
            bottomRight.x -= stepSize/width
            bottomRight.y -= stepSize/height
            newConfig = True
    elif key == ord('l'):
        # Make thr ROI larger (l)
        if bottomRight.x*width + stepSize <= width and \
                bottomRight.y*height + stepSize <= height:
            topLeft.x -= stepSize/width
            topLeft.y -= stepSize/height
            bottomRight.x += stepSize/width
            bottomRight.y += stepSize/height
            newConfig = True

    if newConfig:
        # Send new ROI config data to device.
        config.roi = dai.Rect(topLeft, bottomRight)
        cfg = dai.SpatialLocationCalculatorConfig()
        cfg.addROI(config)
        spatialCalcConfigInQueue.send(cfg)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break


