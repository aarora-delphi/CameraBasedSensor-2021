# Modified Source: https://github.com/guichristmann/edge-tpu-tiny-yolo/blob/master/inference.py

# Python-specific imports
import numpy as np
import tflite_runtime.interpreter as tflite
import sys
import cv2
from time import time
import collections

# Package-specific imports
from tpu_utils_tiny_yolo import *
from detect import BBox

EDGETPU_SHARED_LIB = "libedgetpu.so.1"

def make_interpreter(model_path, edge_tpu=False):
	"""Load the TF-Lite model and delegate to Edge TPU"""
	if edge_tpu:
		interpreter = tflite.Interpreter(model_path=model_path,
						experimental_delegates=[tflite.load_delegate(EDGETPU_SHARED_LIB)])
	else:
		interpreter = tflite.Interpreter(model_path=model_path)

	return interpreter

def inference(interpreter, img, anchors, n_classes, threshold):
	"""Run YOLO inference on the image, returns detected boxes"""
	
	input_details, output_details, net_input_shape = get_interpreter_details(interpreter)

	img_orig_shape = img.shape
	# Crop frame to network input shape
	img = letterbox_image(img.copy(), (416, 416))
	# Add batch dimension
	img = np.expand_dims(img, 0)

	# Set input tensor
	interpreter.set_tensor(input_details[0]['index'], img)
	###start = time()

	# Run model
	interpreter.invoke()

	###inf_time = time() - start
	###print(f"Net forward-pass time: {inf_time*1000} ms.")

	# Retrieve outputs of the network
	out1 = interpreter.get_tensor(output_details[0]['index'])
	out2 = interpreter.get_tensor(output_details[1]['index'])

	# If this is a quantized model, dequantize the outputs
	# Dequantize output
	o1_scale, o1_zero = output_details[0]['quantization']
	out1 = (out1.astype(np.float32) - o1_zero) * o1_scale
	o2_scale, o2_zero = output_details[1]['quantization']
	out2 = (out2.astype(np.float32) - o2_zero) * o2_scale

	# Get boxes from outputs of network
	###start = time()
	_boxes1, _scores1, _classes1 = featuresToBoxes(out1, anchors[[3, 4, 5]], 
					n_classes, net_input_shape, img_orig_shape, threshold)
	_boxes2, _scores2, _classes2 = featuresToBoxes(out2, anchors[[1, 2, 3]], 
					n_classes, net_input_shape, img_orig_shape, threshold)
	###inf_time = time() - start
	###print(f"Box computation time: {inf_time*1000} ms.")

	# This is needed to be able to append nicely when the output layers don't
	# return any boxes
	if _boxes1.shape[0] == 0:
		_boxes1 = np.empty([0, 2, 2])
		_scores1 = np.empty([0,])
		_classes1 = np.empty([0,])
	if _boxes2.shape[0] == 0:
		_boxes2 = np.empty([0, 2, 2])
		_scores2 = np.empty([0,])
		_classes2 = np.empty([0,])

	boxes = np.append(_boxes1, _boxes2, axis=0)
	scores = np.append(_scores1, _scores2, axis=0)
	classes = np.append(_classes1, _classes2, axis=0)

	if len(boxes) > 0:
		boxes, scores, classes = nms_boxes(boxes, scores, classes)

	return boxes, scores, classes

def draw_boxes(image, boxes, scores, classes, class_names):
	"""Draw the bounding boxes on the image with class names"""
	colors = np.random.uniform(30, 255, size=(len(class_names), 3))
	i = 0
	for topleft, botright in boxes:
		# Detected class
		cl = int(classes[i])
		# This stupid thing below is needed for opencv to use as a color
		color = tuple(map(int, colors[cl])) 

		# Box coordinates
		topleft = (int(topleft[0]), int(topleft[1]))
		botright = (int(botright[0]), int(botright[1]))

		# Draw box and class
		cv2.rectangle(image, topleft, botright, color, 2)
		textpos = (topleft[0]-2, topleft[1] - 3)
		score = scores[i] * 100
		cl_name = class_names[cl]
		text = f"{cl_name} ({score:.1f}%)"
		cv2.putText(image, text, textpos, cv2.FONT_HERSHEY_DUPLEX, 0.45, color, 1, cv2.LINE_AA)
		i += 1

def get_interpreter_details(interpreter):
	"""Get input and output tensor details"""
	input_details = interpreter.get_input_details()
	output_details = interpreter.get_output_details()
	input_shape = input_details[0]["shape"]

	return input_details, output_details, input_shape

def get_output(boxes, class_ids, scores, score_threshold):
	"""Returns list of detected objects."""
	count = len(scores)

	Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])

	def make(i):
		topleft, botright = boxes[i]

		ymin, xmin, ymax, xmax = topleft[1], topleft[0], botright[1], botright[0]

		return Object(
				id=int(class_ids[i]),
				score=float(scores[i]),
				bbox=BBox(xmin=xmin,
							ymin=ymin,
							xmax=xmax,
							ymax=ymax).map(int))

	return [make(i) for i in range(count) if scores[i] >= score_threshold]
	
def tpu_tiny_yolo_detection(interpreter, anchors, img, classes, threshold, labeledOutputImage=False):
	"""
	Performs a tiny yolo detection on the tpu.
	interpreter: interpreter object from make_interpreter()
	anchors: 
	img: image for inference 
	classes: classes that are used by the interpreter model
	threshold: float, bounding boxes with a confidence over this threshold will be kept
	labeledOutputImage: bool, creates image with bounding boxes
	"""
	n_classes = len(classes)

	input_details, output_details, input_shape = get_interpreter_details(interpreter)

	# Run inference, get boxes
	boxes, scores, pred_classes = inference(interpreter, img, anchors, n_classes, threshold)
	objs = get_output(boxes, pred_classes, scores, threshold)

	if labeledOutputImage:
		draw_boxes(img, boxes, scores, pred_classes, classes)
	else:
		img = None

	return objs, img
