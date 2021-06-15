# Python-specific imports
import numpy as np
import time
import cv2
import matplotlib.pyplot as plt

# Package-specific imports
from detect_image import tpu_mobilenet_detection
from tpu_inference_tiny_yolo import tpu_tiny_yolo_detection
from tpu_utils_tiny_yolo import get_anchors, get_classes
from YoloVideo import YoloVideo

class tpuVideo(YoloVideo):
  """
    Detection model to identify cars and trucks within a specific region of interest (ROI)
  """

  def __init__(self, net, modelType):
    """
		Inherits variables from the YoloVideo class.
		self.modelType: The tpu model to use for detection. Choose between tpu-mobilenetv2 or tpu-tiny-yolov3.
    """
    super(tpuVideo, self).__init__(net)
    self.modelType = modelType # choose tiny-yolo or mobilenet

  def detect_in_frame(self, output_time=False):
    """
    	Perform inference based on the tpu model and return an object containing id, confidence, and
    	coordinates of bounding boxes in the frame.
    """
    if self.modelType == "tpu-mobilenetv2":
        objs, labeledImage = tpu_mobilenet_detection(self.net, 
            labels=self.labels, image=self.frame, pickedClass=self.pickedClass,
            threshold=self.confidence, labeledOutputImage=False)

    elif self.modelType == "tpu-tiny-yolov3": 
        anchorsPath = "models/tiny_yolo_anchors.txt"
        classesPath = "models/coco.names"

        anchors = get_anchors(anchorsPath)
        classes = get_classes(classesPath)
        
        objs, labeledImage = tpu_tiny_yolo_detection(self.net, anchors, 
            self.frame, classes, self.confidence, labeledOutputImage=False)

    return objs

  def extract_detection_information(self):
    """
    	returns lists of detected bounding boxes, confidences, and class IDs, respectively
    """

    # initialize our lists of detected bounding boxes, confidences,and class IDs, respectively
    boxes = []
    confidences= []
    classIDs = []
    output = self.detect_in_frame()

    #grab frame dimensions
    (H,W) = self.frame.shape[:2]

    # loop over each of the detections
    for detection in output:
        # extract the class ID and confidence (i.e., probability) of the current object detection
        classID = detection.id
        score_confidence = detection.score

        # filter out weak predictions by ensuring the detected
        # probability is greater than the minimum probability
        if score_confidence > self.confidence:
              # scale the bounding box coordinates back relative to
              # the size of the image, keeping in mind that YOLO height
              
              x = int(detection.bbox.xmin)
              y = int(detection.bbox.ymin)
              width = int(detection.bbox.xmax - detection.bbox.xmin)
              height = int(detection.bbox.ymax - detection.bbox.ymin)

              # update our list of bounding box coordinates,confidences and class IDs
              boxes.append([x, y, width, height])
              confidences.append(float(score_confidence))
              classIDs.append(classID)

    self.detection_info = (boxes,confidences,classIDs)