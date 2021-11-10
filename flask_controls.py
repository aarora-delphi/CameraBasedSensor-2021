#!/usr/bin/env python3

### python-packages
from PIL import Image
import numpy as np
import os

### local-packages
import pickle_util
from logger import *

class AppControls():
    def __init__(self):
        self.init_camera()
        self.init_station()
        self.init_focus()
        self.init_roi()
        self.black_image = Image.new('RGB', (300, 300), 'black')

    def init_roi(self):
        """
            Initializes the ROI
        """
        self.pickle_roi = "storage-oak/canvas_roi.pb"
        self.bboxhash = pickle_util.load(self.pickle_roi, error_return = {})

    def init_camera(self):
        """
            Initialize the camera list
        """
        self.cameralist = pickle_util.load("storage-oak/device_id.pb", error_return = ["A", "B", "C"])
        
        # remove after testing is complete
        if self.cameralist != ["A", "B", "C"]:
            for sample in ["172_16_15_70", "B", "C", "D", "E"]:
                self.cameralist.append(sample)

    def init_station(self):
        """
            Initializes the stations to choose from
        """
        self.station_dict = {
        '000':'Not In Use (0)',
        '001':'L1: Menu (1)', 
        '002':'L1: Greet (2)', 
        '003':'L1: Cashier (3)', 
        '004':'L1: Pickup (4)', 
        '005':'L2: Menu (5)', 
        '006':'L2: Greet (6)', 
        '007':'L2: Cashier (7)', 
        '008':'L2: Pickup (8)'
        }
        
        self.station_dict_inv = {value:key for key, value in self.station_dict.items()} # gets inverse
        self.station_choices = list(self.station_dict.values())

    def init_focus(self):
        """
            Initializes the focus levels to choose from
        """
        lensPositionLevel = 15
        lensPositionRange = np.arange(0, 255+(255/(lensPositionLevel-1)), 255/(lensPositionLevel-1)).tolist()
        self.focus_dict = dict([(str(level+1), int(value)) for (level,value) in enumerate(lensPositionRange)])
        self.focus_dict['AUTO'] = -1 # Autofocus
        
        self.focus_dict_inv = {value:key for key, value in self.focus_dict.items()} # gets inverse
        self.focus_choices = list(self.focus_dict.keys())
        self.focus_choices.insert(0, self.focus_choices.pop(self.focus_choices.index('AUTO'))) # Move AUTO to index 0

    def get_station_choices(self):
        return self.station_choices 
    
    def get_focus_choices(self):
        return self.focus_choices
    
    def get_camera_choices(self):
        return self.cameralist

    def get_station(self, camera_id):
        """
            Loads the station for camera_id
        """
        loop_num = pickle_util.load(f"storage-oak/station_{camera_id}.pb", error_return = '255')
        if loop_num == '255':
            return 'Select Station'
        else:
            return self.station_dict[loop_num]

    def set_station(self, camera_id, station):
        """
            Saves the current station for camera_id
        """
        if camera_id in self.cameralist and station in self.station_dict_inv:
            log.info(f"Station Selected for {camera_id}: {station}")
            loop_num = self.station_dict_inv[station]
            pickle_util.save(f"storage-oak/station_{camera_id}.pb", loop_num)
            return True
        else:
            if camera_id not in self.cameralist:
                log.error(f"Camera {camera_id} not in list of cameras {self.cameralist}")
            if station not in self.station_dict_inv:
                log.error(f"Station {station} not in {self.station_dict_inv}")
            return False

    def get_focus(self, camera_id):
        """
            Loads the focus level for camera_id
        """
        focus_num = pickle_util.load(f"storage-oak/focus_{camera_id}.pb", error_return = None)
        if focus_num == None or focus_num not in self.focus_dict_inv:
            return 'X'
        else:
            return self.focus_dict_inv[focus_num]

    def set_focus(self, camera_id, focus):
        """
            Saves the current focus level for camera_id
        """
        if camera_id in self.cameralist and focus in self.focus_dict:
            log.info(f"Focus Level Selected for {camera_id}: {focus} -> {self.focus_dict[focus]}")
            focus_num = self.focus_dict[focus]
            pickle_util.save(f"storage-oak/focus_{camera_id}.pb", focus_num)
            return True
        else:
            if camera_id not in self.cameralist:
                log.error(f"Camera {camera_id} not in list of cameras {self.cameralist}")
            if focus not in self.focus_dict:
                log.error(f"Focus {focus} not in {self.focus_dict}")
            return False

    def get_view(self, camera_id):
        """
            Loads the camera view image path for camera_id
        """
        image_path = f"storage-oak/{camera_id}.png"
        blank_image_path = f"storage-oak/blank.png"

        # check if image exists, else return black image
        if os.path.isfile(image_path):
            return image_path
        else:
            return blank_image_path

    def get_roi(self, camera_id):
        """
            Loads the roi for camera_id
        """
        if camera_id in self.bboxhash and len(self.bboxhash[camera_id]) > 0:
            return self.bboxhash[camera_id][0]
        else:
            default_roi = (50,50,250,250)
            log.warning(f"No ROI found for {camera_id}, returning default ROI {default_roi}")
            return default_roi

    def set_roi(self, camera_id, roi):
        """
            Saves the current roi for camera_id
        """
        # check if values in roi tuple are ints
        def is_int(value):
            return type(value) == int
        
        def in_bounds(value):
            return value >= 0 and value <= 300
        
        valid_roi = False
        if len(roi) == 4 and type(roi) == tuple and \
            is_int(roi[0]) and is_int(roi[1]) and is_int(roi[2]) and is_int(roi[3]) and \
            in_bounds(roi[0]) and in_bounds(roi[1]) and in_bounds(roi[2]) and in_bounds(roi[3]):
            valid_roi = True

        if camera_id in self.cameralist and valid_roi:
            self.bboxhash[camera_id] = [roi] # for one roi only
            log.info(f"{camera_id} ROI Store - {self.bboxhash[camera_id]}")
            pickle_util.save(self.pickle_roi, self.bboxhash)
            return True
        else:
            if camera_id not in self.cameralist:
                log.error(f"Camera {camera_id} not in list of cameras {self.cameralist}")
            if not valid_roi:
                log.error(f"ROI {roi} not valid")
            return False