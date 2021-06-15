# Python-specific imports
import cv2
from datetime import datetime
from shapely.geometry import Polygon
from imutils import resize
from detect_image import make_interpreter

def add_frame_overlay(frame, camera_name="NOT_SPECIFIED"):
	"""
	Add the date, time, and camera name on the frame.
	"""
	timestamp = datetime.now()
	cv2.putText(frame, timestamp.strftime(
		"%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
				cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2) # add date and time

	cv2.putText(frame, "CAMERA: {}".format(camera_name), (10, frame.shape[0] - 40),
				cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2) # add camera name

	return frame

def is_valid_roi(nested_list):
	"""
	Validates the list of [x,y] coordinates that defines the ROI to see if it is a valid shape.
	A valid shape is defined as a Polygon with no intersecting edges ie. no hourglass/bowtie shapes.
	"""
	try:
		shape = Polygon([tuple(i) for i in nested_list]) # Polygon object only accepts list of (x,y) tuples
		return shape.is_valid # determines shape validity
	except Exception as e: # exception if Polygon was not able to be created for any reason ie. bad input
		print(e)
		return False

def prepare_frame_for_display(frame,camera_name="NOT_SPECIFIED"):
	""" Takes in a frame, converts it into bytes as flask requires it and returns the encoded frame. """
	frame = resize(frame, width=800)
	frame = add_frame_overlay(frame,camera_name)
	_,frame = cv2.imencode(".jpg", frame)
	return b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +  bytearray(frame) + b'\r\n' 

def initialize_yolo(modelType="cpu-tiny-yolov3"):
    """Loads model config and weights into darknet and returns object for inference"""
    print("[INFO] loading YOLO from disk...")

    if modelType == "cpu-tiny-yolov3":
        configPath = "yolo-coco/yolov3-tiny.cfg"
        weightsPath = "yolo-coco/yolov3-tiny.weights"
    elif modelType == "cpu-yolov3":
        configPath = "yolo-coco/yolov3.cfg"
        weightsPath = "yolo-coco/yolov3.weights"

    net =  cv2.dnn.readNetFromDarknet(configPath, weightsPath)
    return net



def initialize_tpu(modelType="tpu-tiny-yolov3"):
    """Loads tflite model into tpu and returns object for tpu inference"""
    print("[INFO] loading tflite model into TPU...")
    
    if modelType == "tpu-mobilenetv2":
        model = "models/mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite"
    elif modelType == "tpu-tiny-yolov3":
        model = "models/quant_coco-tiny-v3-relu_edgetpu.tflite"

    interpreter = make_interpreter(model)
    interpreter.allocate_tensors()
    return interpreter