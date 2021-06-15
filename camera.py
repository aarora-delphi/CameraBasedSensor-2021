# Python-specific imports
from imutils.video import VideoStream
from datetime import datetime

class Camera:

	"""
		url: The camera url passed in
		ROI: A list containing all of the coordinates of the Bounding Box.
		VS: A VideoStream object that streams from the camera url
		dimensions: A list containing the width and height of each frame we would receive.
		prepare_ratio: A list containing the ratio of the original frame to the frame that's resized when the frame is preparing for it to be displayed.
		frontend_ratio: A list containing the ratio of the original frame to the frame that's resized when the frame is displayed on the frontend.
		car_count: number of cars that have passed by this camera
	"""

	def __init__(self, url):
		"""
			Basic setup of the object, instanstiates url and starts a new video stream
		"""
		self.url = url
		self.ROI = None
		self.car_count = 0
		#self.frame_delay = 5
		self.initialize_video_stream(url)

	def __iter__(self):
		"""
			Overwrites the default iter function so that you can iterate through this camera.
		"""
		return CameraIterator(self)

	def __repr__(self):
		"""
			String representation of the object.
		"""
		return 'URL: {}, ROI: {}'.format(self.url,self.ROI)

	def set_roi_coordinates(self, coordinates):
		"""
			Updates Region of Interest(ROI) with the coordinates specified from the frontend.
		"""
		self.ROI = coordinates

	def build_video_stream(self, camera_url):
		# Build Stream
		self.VS = VideoStream(src=camera_url).start()
		sample_frame = self.VS.read()
		return sample_frame

	def initialize_video_stream(self,camera_url):
		"""
			Given a camera url, build a stream object and get the dimensions of it.
		"""

		# If we are not able to read a proper frame from the stream, this will fail.
		sample_frame = self.build_video_stream(camera_url)
		assert sample_frame is not None

		# Set the width and height.
		self.dimensions = sample_frame.shape
		self.prepare_ratio = [800/self.dimensions[0],1]
		self.frontend_ratio = [450/(self.dimensions[0]*self.prepare_ratio[0]),800/(self.dimensions[1]*self.prepare_ratio[1])]

	def stop_video_stream(self):
		"""
			Turns off the Video Stream
		"""
		self.VS.stop()

class CameraIterator:
	"""
		This object is created so that you can iterate through a camera object
	"""

	def __init__(self, camera):
		"""
			Basic setup of iterator object.
		"""
		self.camera = camera
		self.frame_counter = 1

	def __next__(self):
		"""
			Allows iterating over this object to get each frame. Ex: "for frame in camera..."
		"""

		# If we are not able to read a proper frame from the stream, this will fail.
		frame = self.camera.VS.read()
		frame_counter = self.frame_counter
	
		restartCount = 0
		while frame is None:
			if restartCount == 5:
				raise Exception("Frame is None")
			self.camera.initialize_video_stream(self.camera.url())
			frame = self.camera.VS.read()
			restartCount+=1
			self.frame_counter = 1;
		now = datetime.now()
		current_time = now.strftime("%H:%M:%S")
		#print("Time: " + current_time + " + ||| Frame Counter: " + str(frame_counter))
		self.frame_counter += 1
		
		return frame

		
"""
	Testing to check for how long it takes to run
"""
if __name__ == '__main__':
	sample = Camera(url = 0)
	i = 0
	for frame in sample:
		if i > 3000:
			break
		print("FROM CAMERA: " + frame)
		i += 1
