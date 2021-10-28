#!/usr/bin/env python3

### python-packages
from pathlib import Path
import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime
import argparse
import multiprocessing

### local-packages
import pickle_util
from find_intersect import intersection_of_polygons
from runtrack import DTrack, DConnect
from runoak import Oak, getOakDeviceIds
from logger import *
from synctrack import TrackSync, synctrackmain

class OakSim(Oak):

    def __init__(self, name = "OAK1", deviceID = None, save_video = None, play_video = None, speed = 1, skip = 0, loop = 0, full = False):
        super().__init__(name, deviceID)
        
        self.save_video = save_video
        self.play_video = play_video
        self.speed = int(speed)
        self.skip = int(int(skip) / self.speed)
        self.loop = loop
        self.full = full
        
        if self.play_video != None:
            self.play_video = str((Path(__file__).parent / Path(self.play_video)).resolve().absolute())

        self.video = np.zeros([300,300,3],dtype=np.uint8) # new
        self.set_preview_size()
        
        if self.save_video != None:
            video_file = f"recording/{self.deviceID}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.mp4"
            self.video_buffer = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc(*'mp4v'), 30, self.preview_size)
            log.info(f"Recording Video of {self.deviceID}")
        
        if self.play_video != None:
            self.cap = cv2.VideoCapture(self.play_video)
 
    def disable_video_loop(self, loop_count):
        self.loop -= loop_count
        
        if self.loop < 0:
            log.info("self.loop ({self.loop}) is less than 0, setting to 0")
            self.loop = 0
        
        log.info(f"Disabled Video Loop for {self.deviceID} - Loops left: {self.loop}")
    
    def get_loop_count(self):
        return self.loop
 
    def set_preview_size(self):
        if self.save_video == '360p':
            self.preview_size = (640, 360)
        elif self.save_video == '720p':
            self.preview_size = (1280, 720)
        elif self.save_video == '1080p':
            self.preview_size = (1920, 1080)
        else:
            self.preview_size = (640, 360)
                  
    def define_pipeline(self):
        """
            OAK camera requires a pipeline. Camera input is passed to the neural network.
            Output is the NN bboxes + the 300x300 and 16x9 camera views
        """
        # Create pipeline
        pipeline = dai.Pipeline()

        # Define sources and outputs
        if self.play_video == None:
            cam = pipeline.createColorCamera()
        else:
            xinFrame = pipeline.createXLinkIn()
            xinFrame.setStreamName("inFrame")
        nn = pipeline.createMobileNetDetectionNetwork()
        manip_crop = pipeline.create(dai.node.ImageManip)

        controlIn = pipeline.createXLinkIn()
        configIn = pipeline.createXLinkIn()
        xoutVideo = pipeline.createXLinkOut() # new
        xoutFrame = pipeline.createXLinkOut()
        xoutNN = pipeline.createXLinkOut()


        controlIn.setStreamName('control')
        configIn.setStreamName('config')
        xoutVideo.setStreamName("video") # new
        xoutFrame.setStreamName("rgb")
        xoutNN.setStreamName("nn")

        # Properties        
        if self.play_video == None:
            cam.setPreviewKeepAspectRatio(True)
            cam.setInterleaved(False)
            cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P) # options - THE_1080_P, THE_4_K, THE_12_MP
            cam.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG)
            cam.setPreviewSize(self.preview_size[0], self.preview_size[1])
            log.info(f"Preview Size - {self.preview_size}")
		
        # Define a neural network that will make predictions based on the source frames
        nn.setBlobPath(self.nnPath)
        nn.setConfidenceThreshold(0.7)
        nn.setNumInferenceThreads(2)
        nn.input.setBlocking(False)

        manip_crop.initialConfig.setResize(300, 300)
        manip_crop.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)
        
        if self.full:
            manip_crop.initialConfig.setResizeThumbnail(300, 300)

        # Linking
        if self.play_video == None:
            cam.preview.link(manip_crop.inputImage)
            cam.preview.link(xoutVideo.input)
            controlIn.out.link(cam.inputControl)
            configIn.out.link(cam.inputConfig) 
        else:
            xinFrame.out.link(manip_crop.inputImage)
            xinFrame.out.link(xoutVideo.input)
       
        manip_crop.out.link(nn.input)
        manip_crop.out.link(xoutFrame.input)
        nn.out.link(xoutNN.input)
        
        return pipeline

    def start_pipeline(self):
        """
            Output Queues used for requesting frame and detections
        """
        log.info("Starting OAK Pipeline...")

        # Output queues will be used to get the rgb frames and nn data from the
        # output streams defined above.
        self.controlQueue = self.device.getInputQueue('control')
        self.configQueue = self.device.getInputQueue('config')
        self.qVideo = self.device.getOutputQueue(name="video", maxSize=4, blocking=False) # new
        self.qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)
        self.qIn_Frame = None
        
        if self.play_video != None:
            self.qIn_Frame = self.device.getInputQueue(name="inFrame", maxSize=4, blocking=False)
        else:
            self.set_autofocus()
            
        self.startTime = time.monotonic()
        self.counter = 0
             
    def inference(self, show_display = False):
        """
            Request request frames and detections
            Check if drawroi.py is in use
        """
        if self.play_video != None and self.cap.isOpened():
            if self.skip > 0:
                read_correctly, video_frame = True, self.frame
                self.skip -= 1
            else:
                for i in range(self.speed):
                    read_correctly, video_frame = self.cap.read()
                
            if read_correctly:
                self.video = video_frame
                video_height, video_width, _ = video_frame.shape
                img = dai.ImgFrame()
                img.setData(self.to_planar(video_frame, (300, 300))) # tried (video_height, video_width) 
                img.setTimestamp(time.monotonic())
                img.setWidth(300) # tried video_width
                img.setHeight(300) # tried video_height
                img.setType(dai.ImgFrame.Type.BGR888p)
        
                # Use input queue to send video frame to device
                self.qIn_Frame.send(img)
            else:
                if self.loop:
                    self.loop -= 1
                    print(f"Loops left for {self.deviceID}: {self.loop}")
                    
                    self.cap = cv2.VideoCapture(self.play_video)    
                else:
                    raise EOFError
        
        inVideo = self.qVideo.tryGet() # new
        inRgb = self.qRgb.tryGet()
        inDet = self.qDet.tryGet()

        if inVideo is not None: # new
            
            if self.play_video == None:
                self.video = inVideo.getCvFrame() # new
            
            if self.save_video != None:
                self.video_buffer.write(self.video)
        
        if inRgb is not None:
            self.frame = inRgb.getCvFrame()

        if inDet is not None:
            self.detections = inDet.detections
            self.counter += 1

        self.check_drawroi() # stores frame for use in drawroi.py
    
    def to_planar(self, arr: np.ndarray, shape: tuple) -> np.ndarray:
        return self.center_crop(arr, shape).transpose(2, 0, 1).flatten()
    
    def center_crop(self, img, dim):
	    """Returns center cropped image
	        Args:
	        img: image to be center cropped
	        dim: dimensions (width, height) to be cropped
	    """
	    width, height = img.shape[1], img.shape[0]
	    mid_x, mid_y = int(width/2), int(height/2)
	    crop_img = img[:, mid_x-mid_y:mid_x+mid_y] # width is center cropped to height
	    crop_img = cv2.resize(crop_img, dim) # 1:1 aspect ratio image is scaled to dim
	    
	    return crop_img

    def release_resources(self):
        """
            Releases the video buffer if present and closes device
        """
        # release video buffer to save video
        if self.save_video != None:
            self.video_buffer.release()
            log.info(f"Released Video Object of {self.deviceID}")
        
        log.info(f"Closing Device {self.deviceID}")
        self.device.close() # close device

def parse_arguments():
    """
        Parses Command Line Arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-track', '--track', action="store_true", help="Send messages to track system")
    parser.add_argument('-record', '--record', choices=['360p', '720p', '1080p'], default = None, help="Save Recording of connected OAK")
    parser.add_argument('-video', '--video', action="store_true", default = None, help="Run Video as Input")
    parser.add_argument('-speed', '--speed', default = 1, type = int, help="Speed of Video Playback - Default: 1")
    parser.add_argument('-skip', '--skip', default = 0, type = int, help="Frames to delay video playback - Compounded with # of OAK")
    parser.add_argument('-loop', '--loop', action="store_true", default = False, help="Loop Video Playback a Million Times")
    parser.add_argument('-full', '--full', action="store_true", default = False, help="Use letterboxing for 16:9 aspect ratio frame")
    args = parser.parse_args()
    
    if args.video == True:
       args.video = './video/video08312021.mp4' 
       
    return args

def create_camera_track_list(camera_track_list, args, ignore_station = ['255'], order_station = False):
    """
        Initializes list of Oak and DTrack Objects for each OAK Device
    """
    oak_device_ids = getOakDeviceIds()
    log.info(f"Found {len(oak_device_ids)} OAK DEVICES - {oak_device_ids}")
    pickle_util.save("storage-oak/device_id.pb", oak_device_ids)
    assert len(oak_device_ids) != 0

    def order_oak_by_station(elem):
        station = pickle_util.load(f"storage-oak/station_{elem}.pb", error_return = '255')
        return int(station) if station != '000' else 255

    if order_station:
        oak_device_ids.sort(key=order_oak_by_station)    

    for count, device_id in enumerate(oak_device_ids):
        station = pickle_util.load(f"storage-oak/station_{device_id}.pb", error_return = '255')
        log.info(f"OAK DEVICE: {device_id} - STATION: {station}")
        if station in ignore_station:
            log.error(f"Invalid Station {station} - Abort {device_id} Initialization")
            continue

        cam = getCam(device_id, args, count); cam.organize_pipeline()
        tck = DTrack(name = station, connect = args.track)
        camera_track_list.append([cam, tck])

def getCam(device_id, args, count):
    """
        Returns the Oak Object
    """
    return OakSim(deviceID = device_id, save_video = args.record, play_video = args.video, \
                  speed = args.speed, skip = args.skip*count, loop = 3 if args.loop else 0, full = args.full) 

if __name__ == "__main__":
    log.info("Started runsim Process\n\n")
    args = parse_arguments()
    ### dconn = DConnect(connect = args.track)
    
    if args.track:
        work_queue = multiprocessing.Queue()
        synctck = multiprocessing.Process(target=synctrackmain, args=(work_queue,True), daemon=True)
        synctck.start()
        log.info("Started synctrack Process")
    
    camera_track_list = []
    create_camera_track_list(camera_track_list, args, ignore_station = ['255', '000'], order_station = True)
    should_run = True
    
    videoComplete = [] # store finished OAK videos
    
    while should_run:
        for (camera, track) in camera_track_list:
            try:
                camera.inference()
                numCars = camera.detect_intersections(show_display = True)
                to_send = track.log_car_detection(numCars)
  
                if args.track:
                    if to_send != None:
                        work_queue.put(to_send) 
                    
                    if not synctck.is_alive():
                        synctck = multiprocessing.Process(target=synctrackmain, args=(work_queue,False), daemon=True)
                        synctck.start()
                        log.info("Restarted synctrack Process")
                
                if cv2.waitKey(1) == ord('q'):
                    if args.video and args.loop:
                        loop_count = camera_track_list[0][0].get_loop_count()
                        for (camera, track) in camera_track_list:
                            camera.disable_video_loop(loop_count)
                    else:
                        should_run = False; break  

            except EOFError:
                if camera.deviceID not in videoComplete:
                    log.info(f"End of Video for {camera.deviceID}")
                    videoComplete.append(camera.deviceID)
                    if len(videoComplete) == len(camera_track_list):
                        should_run = False; break 
        
            # these 4 exceptions same as runoak.py
            except KeyboardInterrupt:
                log.info(f"Keyboard Interrupt")
                should_run = False; break

            #except BrokenPipeError:
            #    log.error("Lost Connection to Track")
            #    
            #    if args.track:
            #        synctck.terminate()
            #        time.sleep(0.5)
            #        synctck.close()
            #        log.info(f"Terminated synctrack Process")
            #    
            #    dconn.close_socket()
            #    dconn = DConnect(connect = args.track)
            #    
            #    if args.track:                    
            #        synctck = multiprocessing.Process(target=synctrackmain, args=(dconn,False), daemon=True)
            #        synctck.start()
            #        log.info("Restarted synctrack Process")              
            #
            #    time.sleep(0.5)
            #    for i in range(len(camera_track_list)):
            #        camera_track_list[i][1].set_connect(dconn.get_conn()) # reset track connection
 
            except RuntimeError:
                if camera.error_flag == 0:
                    log.exception(f"Runtime Error for {camera.deviceID}")
                    camera.device.close() # close device
                    camera.error_flag = 1
                if camera.device.isClosed() and camera.deviceID in getOakDeviceIds(): # TO DO - make non-blocking
                    log.info(f"Found {camera.deviceID} - Reconnecting to OAK Pipeline")
                    camera.device = dai.Device(camera.pipeline, camera.device_info)
                    camera.start_pipeline()
                    camera.error_flag = 0
        
            except:
                log.exception(f"New Exception")
                should_run = False; break          

    # dconn.close_socket()
    
    for (camera, track) in camera_track_list:
        camera.release_resources()
