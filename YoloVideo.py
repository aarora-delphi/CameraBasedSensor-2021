# Python-specific imports
import numpy as np
import time
import cv2
import matplotlib.pyplot as plt

# Package-specific imports
from find_intersect import intersection_of_polygons
from detect_image import load_labels

class YoloVideo:
	"""
		Detection model to identify cars and trucks within a specific region of interest (ROI)
	"""

	def __init__(self, net):
		"""
			self.frame: frame from stream
			self.ROI: nested list defining region of intereest in frame in which we detect vehicles
			self.confidence: minimum probability to filter weak detections
			self.threshold: threshold when applying non-maxima suppression
		"""
		self.net = net
		self.frame = None
		self.ROI = []
		self.confidence = 0.20
		self.threshold = 0.3
		self.debug = True
		self.labels = load_labels(self.get_yolo_labels()) if self.get_yolo_labels() else {}
		self.pickedClass = ['car', 'motorcycle', 'truck']
		self.detection_info = None
		self.DEBUG_IMAGE = np.ones([100,100,3],dtype=np.uint8) * 55
		

	def set_frame_and_roi(self,frame,camera):
		"""
			resize the ROI to match the frame
		"""
		self.frame = frame

		# Ratios needed to resize the ROI coordinates to match the original frame
		x_ratio = camera.frontend_ratio[0]* camera.prepare_ratio[0]
		y_ratio = camera.frontend_ratio[1]* camera.prepare_ratio[1]

		self.ROI = []

		for coord in camera.ROI:
			self.ROI.append([coord[0]/x_ratio,coord[1]/y_ratio])

	def get_yolo_labels(self):
		"""
			return the COCO class labels our YOLO model was trained on
		"""
		labels_file = "models/coco_labels.txt"
		return labels_file


	def initiailize_colors(self, labels):
		"""
			return a list of colors to represent each possible class label
		"""
		np.random.seed(42)
		return  np.random.randint(0,255, size=(len(labels), 3), dtype="uint8")

	def get_layer_names(self):
		"""
			determine only the *output* layer names that we need from YOLO
			returns layer names
		"""
		ln = self.net.getLayerNames()
		return [ln[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]

	def detect_in_frame(self, output_time=False):
		"""
			detect vehicle in frame
			returns layer outputs, which contains class id and confidence probabilities
		"""

		#get yolo object and layer names
		#self.net = self.get_yolo_object()
		ln = self.get_layer_names()

		# construct a blob from the input frame and then perform a forward
		# pass of the YOLO object detector, giving us our bounding boxes
		# and associated probabilities
		blob = cv2.dnn.blobFromImage(self.frame, 1 / 255.0, (416, 416),swapRB=True, crop=False)
		self.net.setInput(blob)
		start = time.time()
		layerOutputs = self.net.forward(ln)
		end = time.time()
		if output_time == True:
			elap = (end - start)
			print("[INFO] single frame took {:.4f} seconds".format(elap))
		return layerOutputs

	def extract_detection_information(self):
		"""
			returns lists of detected bounding boxes, confidences, and class IDs, respectively
		"""

		# initialize our lists of detected bounding boxes, confidences,and class IDs, respectively
		boxes = []
		confidences= []
		classIDs = []
		layerOutputs = self.detect_in_frame()

		#grab frame dimensions
		(H,W) = self.frame.shape[:2]

		# loop over each of the layer outputs
		for output in layerOutputs:
			# loop over each of the detections
			for detection in output:
				# extract the class ID and confidence (i.e., probability) of the current object detection
				scores = detection[5:]
				classID = np.argmax(scores)
				score_confidence = scores[classID]

				# filter out weak predictions by ensuring the detected
				# probability is greater than the minimum probability
				if score_confidence > self.confidence:
					# scale the bounding box coordinates back relative to
					# the size of the image, keeping in mind that YOLO height
					box = detection[0:4] * np.array([W, H, W, H])
					(centerX, centerY, width, height) = box.astype("int")

					# use the center (x, y)-coordinates to derive the top
					# and and left corner of the bounding box
					x = int(centerX - (width / 2))
					y = int(centerY - (height / 2))

					# update our list of bounding box coordinates,confidences and class IDs
					boxes.append([x, y, int(width), int(height)])
					confidences.append(float(score_confidence))
					classIDs.append(classID)

		self.detection_info = (boxes,confidences,classIDs)

	def apply_suppression(self):
		"""
			apply non-maxima suppression to the detected bounding boxes
		"""
		boxes = self.detection_info[0]
		confidences = self.detection_info[1]

		idxs = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence, self.threshold)
		return idxs

	def detect_intersections(self):
		"""
			detects if the detected vehicle is within the ROI
			self.net: yolo object
		"""

		self.extract_detection_information()

		idxs = self.apply_suppression()
		LABELS = self.labels
		boxes = self.detection_info[0]
		confidences = self.detection_info[1]
		classIDs = self.detection_info[2]
		
		trackObj = None
		
		if self.debug:
			self.draw_debug_setup()

		#ensure at least one detection exists
		if len(idxs) > 0:
			#loop over indexes we are keeping
			carAmount = 0
			for i in idxs.flatten():
				#extract the bounding box coordinates
				(x, y) = (boxes[i][0], boxes[i][1])
				(w, h) = (boxes[i][2], boxes[i][3])

				#get shape of bounding box to get intersection with ROI
				bounding_box = [(x,y),(x,y+h),(x+w,y+h),(x+w,y),(x,y)]		
						
				bbox_class = LABELS.get(classIDs[i], classIDs[i])
				
				intersects_flag = False
				
				if bbox_class in self.pickedClass:
					intersects_flag = intersection_of_polygons(self.ROI,bounding_box)
					if intersects_flag:
						carAmount += 1
						
						#print(f"DETECTED: {LABELS.get(classIDs[i], classIDs[i])}, CONFIDENCE: {confidences[i]}")
						#print("Intersection with ROI: TRUE")
				
				if self.debug:
					self.draw_debug_bbox([x, y, w, h], intersects_flag, bbox_class, confidences[i])
            			
			return carAmount, self.DEBUG_IMAGE
		return 0, self.DEBUG_IMAGE 
	
	def draw_debug_setup(self): #draw ROI and setup text
		self.DEBUG_IMAGE = self.frame
			
		cv2.putText(self.DEBUG_IMAGE, text=f"DETECTION MODE", 
					org=(int(self.DEBUG_IMAGE.shape[1]*0.75), 40), fontFace=cv2.FONT_HERSHEY_SIMPLEX, 
					fontScale=1, color=(150,255,255), thickness=2, lineType=cv2.LINE_AA)	
			
		cv2.polylines(self.DEBUG_IMAGE, [np.asarray(self.ROI, np.int32).reshape((-1,1,2))], True, (150,255,255), 3)
	
	
	def draw_debug_bbox(self, bbox, intersects_flag, bbox_class, confidence):
		x, y, w, h = bbox
		
		debugColor = (255, 0, 0) # blue
		if bbox_class in self.pickedClass:
			debugColor = (0, 0, 255) # red
			if intersects_flag:
				debugColor = (0,255,0) # green
	
		cv2.rectangle(self.DEBUG_IMAGE, (x, y), (x+w, y+h), debugColor, 2)
		cv2.putText(self.DEBUG_IMAGE, text=f"{bbox_class}: {int(confidence*100)}%", 
			org=(x,y-5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, 
			fontScale=1, color=debugColor, thickness=2, lineType=cv2.LINE_AA)