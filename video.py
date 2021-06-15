from camera import Camera
from datetime import datetime
import cv2

class Video(Camera):

	def __init__(self,url):
		super(Video, self).__init__(url)

	def __iter__(self):
		return VideoIterator(self)

	def build_video_stream(self,video_path):
		self.VS = cv2.VideoCapture(video_path) 
		grabbed, sample_frame = self.VS.read()
		return sample_frame



class VideoIterator:
	def __init__(self, video):
		self.video = video
		self.frame_counter = 1
		vidCap = cv2.VideoCapture(self.video.url)
		self.fps = vidCap.get(cv2.CAP_PROP_FPS)
		self.frameCount = vidCap.get(cv2.CAP_PROP_FRAME_COUNT)
		self.timeTracker = datetime.now().strftime("%H:%M:%S")
		self.timeCounter = 0;
		if(self.fps > 10):
			self.ReadFrameRate = int(self.fps / 10)
		else:
			self.ReadFrameRate = 1
		if(self.ReadFrameRate == 0):
			self.ReadFrameRate = 1

		#print("fps: " + str(self.fps) + " ||| frameCount: " + str(self.frameCount))
		#self.VS = cv2.VideoCapture(self.video.url)

	def __next__(self):
		frame_counter = self.frame_counter
		readFrameRate = self.ReadFrameRate
		grabbed, frame = self.video.VS.read()
		skippedFrames = False
		if(self.frame_counter != 1):
			#print("self.frame_counter != 1")
			#print("self.frame_counter: " + str(self.frame_counter) + " ||| readFrameRate")
			#print(str(self.frame_counter % readFrameRate != 0))
			while (self.frame_counter % readFrameRate != 0):
				skippedFrames = True
				#print("I am in here")
				grabbed, frame = self.video.VS.read()
				self.frame_counter += 1
		#else:
			#print("I did not go in there")


		if grabbed == False: 
			self.video.initialize_video_stream(self.video.url)
			grabbed,frame = self.video.VS.read()
			self.frame_counter = 1
		now = datetime.now()
		current_time = now.strftime("%H:%M:%S")
		#print("Time: " + current_time + " + ||| Frame Counter: " + str(self.frame_counter))
		#if(self.frame_counter == 1 | skippedFrames == False):
		self.frame_counter += 1
		if(self.fps < 10):
			if(self.timeTracker != current_time):
				self.timeTracker = current_time
				self.timeCounter = 0
			else:
				self.timeCounter += 1
				if(self.timeCounter >= self.fps):
					timeHolder = self.timeTracker
					while(self.timeTracker == timeHolder):
						self.timeTracker = datetime.now().strftime("%H:%M:%S")
					self.timeCounter = 0


		return frame
