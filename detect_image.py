# Lint as: python3
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#		 https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Modified Source: https://github.com/google-coral/tflite/blob/master/python/examples/detection/detect_image.py

"""Example using TF Lite to detect objects in a given image."""

# Python-specific imports
import argparse
import time
import numpy as np
from PIL import Image
from PIL import ImageDraw
import tflite_runtime.interpreter as tflite
import platform

# Package-specific imports
import detect

EDGETPU_SHARED_LIB = {
	'Linux': 'libedgetpu.so.1',
	'Darwin': 'libedgetpu.1.dylib',
	'Windows': 'edgetpu.dll'
}[platform.system()]


def load_labels(path, encoding='utf-8'):
	"""Loads labels from file (with or without index numbers).

	Args:
		path: path to label file.
		encoding: label file encoding.
	Returns:
		Dictionary mapping indices to labels.
	"""
	with open(path, 'r', encoding=encoding) as f:
		lines = f.readlines()
		if not lines:
			return {}

		if lines[0].split(' ', maxsplit=1)[0].isdigit():
			pairs = [line.split(' ', maxsplit=1) for line in lines]
			return {int(index): label.strip() for index, label in pairs}
		else:
			return {index: line.strip() for index, line in enumerate(lines)}


def make_interpreter(model_file):
	"""Generate interpreter object, used for tpu models"""
	model_file, *device = model_file.split('@')
	return tflite.Interpreter(
			model_path=model_file,
			experimental_delegates=[
					tflite.load_delegate(EDGETPU_SHARED_LIB,
					{'device': device[0]} if device else {})
			])


def draw_objects(draw, objs, labels):
	"""Draws the bounding box and label for each object."""
	for obj in objs:
		bbox = obj.bbox
		draw.rectangle([(bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax)], outline='red')
		draw.text((bbox.xmin + 10, bbox.ymin + 10),'%s\n%.2f' % (labels.get(obj.id, obj.id), obj.score), fill='red')

def tpu_mobilenet_detection(interpreter, labels, image, pickedClass, threshold=0.25, labeledOutputImage=True):
	"""
		Detection for mobilenet model, 
		returns filtered outputs: only outputs with the labels that we care about 
	"""
	#interpreter = make_interpreter(model)
	#interpreter.allocate_tensors()

	image = Image.fromarray(image)
	scale = detect.set_input(interpreter, image.size, lambda size: image.resize(size, Image.ANTIALIAS))
	start = time.perf_counter()
	interpreter.invoke()
	inference_time = time.perf_counter() - start
	objs = detect.get_output(interpreter, threshold, scale)
	
	final_objs = []

	#Filter out labels so that we only use the labels we want to detect for
	for obj in objs:
		label_name = labels.get(obj.id, obj.id)
		if label_name in pickedClass:
				final_objs.append(obj)

	image = None

	if labeledOutputImage:
		image = image.convert('RGB')
		draw_objects(ImageDraw.Draw(image), objs, labels)
		image = np.array(image)

	return final_objs, image

