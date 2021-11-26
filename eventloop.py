#!/usr/bin/env python3

### FILE NOT IN USE ###
### File Sets up the Event Loop for Oak() and OakSim() Classes ###

### python-packages
import cv2
import depthai as dai
import argparse
import multiprocessing
import time

### local-packages
import pickle_util
from runtrack import DTrack
from synctrack import synctrackmain
from runoak import Oak
from runsim import OakSim
from logger import *

class OakLoop():
    def __init__(self):
        self.camera_track_list = []
        self.should_run = True
        self.start_time = time.time()
        
        self.set_custom_parameters()
        self.parse_arguments()
        self.setup_synctrack()
        self.setup_cameralist()
        self.set_active_devices()

    def set_custom_parameters(self):
        """
            Set parameters unique to OakLoop
        """
        self.ignore_station = ['255']


    def parse_arguments(self):
        """
            Parses Command Line Arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-track', '--track', action="store_true", help="Send messages to track system")
        self.args = parser.parse_args()
        log.info(f"Started runoak Process with {self.args}\n\n")


    def getCam(self, device_id, count):
        """
            Returns the Oak Object
        """
        return Oak(deviceID = device_id) 


    def setup_synctrack(self):
        """
            Sets up synctrack if specified by self.args
        """
        if self.args.track:
            self.work_queue = multiprocessing.Queue()
            self.synctck = multiprocessing.Process(target=synctrackmain, args=(self.work_queue,True), daemon=True)
            self.synctck.start()
            log.info("Started synctrack Process")


    def add_camera(self, device_id):
        """
            Adds [camera, track] to self.camera_track_list
        """
        station = pickle_util.load(f"storage-oak/station_{device_id}.pb", error_return = '255')
        log.info(f"OAK DEVICE: {device_id} - STATION: {station}")
        
        if station in self.ignore_station:
            log.error(f"Invalid Station {station} - Abort {device_id} Initialization")
            return

        cam = self.getCam(device_id = device_id, count = len(self.camera_track_list)); cam.organize_pipeline()
        tck = DTrack(name = station, connect = self.args.track)
        self.camera_track_list.append([cam, tck])


    def remove_camera(self, device_id):
        """
            Remove Camera from self.camera_track_list
        """
        if device_id in self.active_devices:
            device_index = self.active_devices.index(device_id)
            camera, track = self.camera_track_list.pop(device_index)
            camera.release_resources()
            self.set_active_devices()


    def set_active_devices(self):
        """
            Sets a list of active devices
        """
        self.active_devices = [camera.deviceID for (camera, track) in self.camera_track_list]
        pickle_util.save("storage-oak/device_id.pb", self.active_devices)


    def check_new_devices(self):
        """
            Adds new cameras to self.camera_track_list
        """
        for device_id in self.find_oak_devices():
            if device_id not in self.active_devices:
                self.add_camera(device_id)
                self.set_active_devices()
                log.info(f"Added Device {device_id} - All Active Devices: {self.active_devices}")


    def setup_cameralist(self):
        """
            Sets up cameralist 
        """
        found_devices = self.find_oak_devices()
        log.info(f"Found {len(found_devices)} OAK DEVICES - {found_devices}")
        pickle_util.save("storage-oak/device_id.pb", found_devices)

        def order_oak_by_station(elem):
            station = pickle_util.load(f"storage-oak/station_{elem}.pb", error_return = '255')
            return int(station) if station != '000' else 255

        found_devices.sort(key=order_oak_by_station) 

        for device_id in found_devices:
            self.add_camera(device_id)


    def find_oak_devices(self):
        """
            Checks for available OAK Devices
        """
        found_devices = [device_info.getMxId() for device_info in dai.Device.getAllAvailableDevices() if device_info.getMxId() != '<error>']
        return found_devices   


    def run_event_loop(self):
        """
            Event Loop
        """
        while self.should_run:
            for (camera, track) in self.camera_track_list:
                try:
                    self.oak_event(camera, track)
                    if self.check_quit(camera, track):
                        self.should_run = False; break
                except RuntimeError:
                    self.except_runtime_error(camera, track)
                except EOFError:
                    if self.except_eof_error(camera, track):
                        self.should_run = False; break
                except KeyboardInterrupt:
                    log.info(f"Keyboard Interrupt")
                    self.should_run = False; break
                except Exception:
                    log.exception(f"New exception")
                    self.should_run = False; break
            
            if time.time() - self.start_time > 30: # repeat every 30 seconds
                self.start_time = time.time()
                self.check_synctrack()
                self.check_new_devices() # presents slight delay

        for (camera, track) in self.camera_track_list:
            camera.release_resources()


    def check_synctrack(self):
        """
            Restarts synctrack process if not alive
        """
        if self.args.track and not self.synctck.is_alive():
            self.synctck = multiprocessing.Process(target=synctrackmain, args=(self.work_queue,False), daemon=True)
            self.synctck.start()
            log.info("Restarted synctrack Process")   


    def oak_event(self, camera, track):
        """
            Events to run for an OAK Device
        """
        
        camera.inference()
        numCars = camera.detect_intersections(show_display = True)
        to_send = track.log_car_detection(numCars)
        
        if self.args.track:
            if to_send != None:
                self.work_queue.put(to_send) 
                camera.update_event(to_send)
    

    def check_quit(self, camera, track):
        """
            Checks if 'q' key was clicked on opencv window
        """
        return cv2.waitKey(1) == ord('q')


    def except_runtime_error(self, camera, track):
        """
            Restarts OAK Device if Runtime Error Occurs
        """
        if camera.error_flag == 0:
            log.exception(f"Runtime Error for {camera.deviceID}")
            camera.device.close() # close device
            camera.error_flag = 1
        if camera.device.isClosed() and camera.deviceID in self.find_oak_devices(): # TO DO - make non-blocking
            log.info(f"Found {camera.deviceID} - Reconnecting to OAK Pipeline")
            camera.device = dai.Device(camera.pipeline, camera.device_info)
            camera.start_pipeline()
            camera.error_flag = 0


    def except_eof_error(self, camera, track):
        """
            Only used by OakSim - placeholder
        """
        return False


class OakSimLoop(OakLoop):

    def set_custom_parameters(self):
        """
            Set parameters unique to OakSimLoop
        """
        self.ignore_station = ['000', '255']
        self.video_complete = []


    def parse_arguments(self):
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
        parser.add_argument('-sync', '--sync', action="store_true", default = False, help="Sync RGB output with NN output")
        self.args = parser.parse_args()
        
        if self.args.video == True:
            # self.args.video = './video/video08312021.mp4'
            # self.args.video = './video/video10282021.mp4'
            self.args.video = './video/video10282021-long.mp4'
        
        log.info(f"Started runsim Process with {self.args}\n\n")


    def getCam(self, device_id, count):
        """
            Returns the Oak Object
        """
        return OakSim(deviceID = device_id, \
                    save_video = self.args.record, \
                    play_video = self.args.video, \
                    speed = self.args.speed, \
                    skip = self.args.skip*count, \
                    loop = 1000000 if self.args.loop else 0, \
                    full = self.args.full, \
                    sync = self.args.sync) 


    def check_quit(self, camera, track):
        """
            Checks if 'q' key was clicked on opencv window
        """
        if cv2.waitKey(1) == ord('q'):
            if self.args.video and self.args.loop:
                loop_count = self.camera_track_list[0][0].get_loop_count()
                for (camera, track) in self.camera_track_list:
                    camera.disable_video_loop(loop_count)
            else:
                return True
        
        return False


    def except_eof_error(self, camera, track):
        """
            Only used by OakSim - breaks out of event_loop when all videos are complete
        """
        if camera.deviceID not in self.video_complete:
            log.info(f"End of Video for {camera.deviceID}")
            self.video_complete.append(camera.deviceID)
            if len(self.video_complete) == len(self.camera_track_list):
                return True
        return False

if __name__ == "__main__":
    app = OakSimLoop()
    app.run_event_loop()