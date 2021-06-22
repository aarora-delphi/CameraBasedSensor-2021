# first, import all necessary modules
from pathlib import Path
import cv2
import depthai
import numpy as np

# https://github.com/chuanqi305/MobileNet-SSD
# https://github.com/openvinotoolkit/open_model_zoo/tree/master/models/public/mobilenet-ssd

nnPath = str((Path(__file__).parent / Path(
    './models/OpenVINO_2021_2/mobilenet-ssd_openvino_2021.2_6shave.blob')).resolve().absolute())

# ------------------------------------------------------------------------------
# 1. Create a pipeline object.
# ------------------------------------------------------------------------------
# Pipeline tells DepthAI what operations to perform when running
# You define all of the resources used and flows.
pipeline = depthai.Pipeline()

# ------------------------------------------------------------------------------
# 2. Create camera and neural network nodes.
# ------------------------------------------------------------------------------
# First, we want the Color camera as the output
cam = pipeline.createColorCamera()
cam.setPreviewSize(300, 300)
cam.setInterleaved(False)

# Next, we want a neural network that will produce the detections. The NueralNetwork
# class will produce a NNData object which can be parsed for detection data. Other,
# more specific, neural network classes are also available of the type DetectionNetworks
# which produce ImgDetection messages as output.
nn = pipeline.createNeuralNetwork()

# Blob is the Neural Network file, compiled for MyriadX. It contains both the
# definition and weights of the model
nn.setBlobPath(nnPath)

# Next, we link the camera 'preview' output to the neural network detection input,
# so that it can produce detections
cam.preview.link(nn.input)

# ------------------------------------------------------------------------------
# 3. Create XLinkOut nodes for camera and neural network outputs.
# ------------------------------------------------------------------------------

xoutFrame = pipeline.createXLinkOut()
xoutFrame.setStreamName("rgb")
cam.preview.link(xoutFrame.input)

# The same XLinkOut mechanism will be used to receive nn results
xoutNN = pipeline.createXLinkOut()
xoutNN.setStreamName("nn")
nn.out.link(xoutNN.input)

# ------------------------------------------------------------------------------
# 4. Create a device object and start the pipeline.
# ------------------------------------------------------------------------------
# The Pipeline is now finished, and we need to find an available device to run
# our pipeline on.
device = depthai.Device(pipeline)
# And start. From this point, the Device will be in a "running" mode and will
# start sending data via XLink
device.startPipeline()

# ------------------------------------------------------------------------------
# 5. Defines output queues with stream names to consume device results.
# ------------------------------------------------------------------------------
qRgb = device.getOutputQueue("rgb")
qDet = device.getOutputQueue("nn")

# Create variables to store camera image frames and nn detections.
frame = None
bboxes = []

# Since the bboxes returned by nn have values from <0..1> range, they need to be
# multiplied by frame width/height to receive the actual position of the bounding
# box on the image nn data (bounding box locations) are in <0..1> range - they
# need to be normalized with frame width/height
def frameNorm(frame, bbox):
    normVals = np.full(len(bbox), frame.shape[0])
    normVals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

# ------------------------------------------------------------------------------
# 6. Main host-side application loop
# ------------------------------------------------------------------------------
while True:
    # we try to fetch the data from nn/rgb queues. tryGet will return either the
    # data packet or None if there isn't any
    inRgb = qRgb.tryGet()
    inDet = qDet.tryGet()

    if inRgb is not None:
        # When data from rgb stream is received, we need to transform it from 1D
        # flat array into 3 x height x width one. The new convenience function in
        # the Gen2 API handles the required conversions.
        frame = inRgb.getCvFrame()

    if inDet is not None:
        # When data from nn is received, it is also represented as a 1D array
        # initially, just like rgb frame. The neural network node we defined
        # above using the NeuralNetwork class produces a NNData output message
        # which can be parsed by getFirstLayerFp16().
        bboxes = np.array(inDet.getFirstLayerFp16())

        # The nn detections array is a fixed-size (and very long) array. The actual
        # data from nn is available from the beginning of an array, and is finished
        # with -1 value, after which the array is filled with zeros, so we need to
        # crop the array so that only the data from nn are left.
        bboxes = bboxes[:np.where(bboxes == -1)[0][0]]

        # Next, the single NN results consists of 7 values:
        # [ id, label, confidence, x_min, y_min, x_max, y_max]
        # that's why we reshape the array from 1D into 2D array - where each row
        # is a nn result with 7 columns
        bboxes = bboxes.reshape((bboxes.size // 7, 7))

        # Finally, we want only these results for which confidence (ranged <0..1>)
        # is greater than some detection threshold. For this example, we are only
        # interested in bounding boxes (so last 4 columns).
        detection_threshold = 0.8
        bboxes = bboxes[bboxes[:, 2] > detection_threshold][:, 3:7]

    if frame is not None:
        for raw_bbox in bboxes:
            # for each bounding box, we first normalize it to match the frame size
            bbox = frameNorm(frame, raw_bbox)
            # and then draw a rectangle on the frame to show the actual result
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]),
                          (255, 0, 0), 2)

        # After all the drawing is finished, we show the frame on the screen
        cv2.imshow("preview", frame)

    # at any time, you can press "q" and exit the main loop, therefore exiting the program itself
    if cv2.waitKey(1) == ord('q'):
        break
