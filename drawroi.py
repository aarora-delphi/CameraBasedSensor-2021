#!/usr/bin/env python3

### python-packages
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import numpy as np
import os

### local-packages
import pickle_util
from logger import *

class ScrolledCanvas(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canv = Canvas(self, bd=0, highlightthickness=0)
        self.hScroll = Scrollbar(self, orient='horizontal',
                                 command=self.canv.xview)
        self.hScroll.grid(row=1, column=0, sticky='we')
        self.vScroll = Scrollbar(self, orient='vertical',
                                 command=self.canv.yview)
        self.vScroll.grid(row=0, column=1, sticky='ns')
        self.canv.grid(row=0, column=0, sticky='nsew', padx=4, pady=4)        
        self.canv.configure(xscrollcommand=self.hScroll.set,
                            yscrollcommand=self.vScroll.set)
        
class MyApp(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main = Canvas(self, width=300, height=300, bg = "white", cursor="cross")
        self.main.pack(side="top", fill="both", expand=True)

        self.cameralist = pickle_util.load("storage-oak/device_id.pb", error_return = ["A", "B", "C"])
        log.info(f"Camera List: {self.cameralist}")
        
        self.camerapointer = 0
        self.name = self.cameralist[self.camerapointer]
        
        self.pickle_roi = "storage-oak/canvas_roi.pb"
        self.bboxhash = pickle_util.load(self.pickle_roi, error_return = {})
        
        self.currentImage = {}
        self.initialize_controls()
        self.refresh_gui()
        
        self.can_refresh = True

    def refresh_gui(self):
        """
            Sets all the tkinter parameters for a given camera identified by self.name 
        """
        self.set_view()
        self.set_title()
        self.station_load()
        self.focus_load()

    def initialize_controls(self):
        """
            Initialize Button and Mouse Controls for tkinter application
        """
        
        # mouse controls
        self.main.bind('<ButtonPress-1>', self.on_mouse_down)
        self.main.bind('<B1-Motion>', self.on_mouse_drag)
        self.main.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.main.bind('<Button-3>', self.on_right_click)

        # button controls
        self.button_next = Button(self, text = "Next", command = self.next)
        self.button_next.pack(side=RIGHT, fill="both", expand=True)
        self.button_prev = Button(self, text = "Prev", command = self.prev)
        self.button_prev.pack(side=LEFT, fill="both", expand=True)
        
        self.button_save = Button(self, text = "Refresh", command = self.set_view)
        self.button_save.pack(side="top", fill="both", expand=True)
        self.button_clear = Button(self, text = "Clear", command = self.clear_all)
        self.button_clear.pack(side="top", fill="both", expand=True)
        
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
        self.station_var = StringVar(self)
        self.station = OptionMenu(self, self.station_var, *self.station_choices, command=self.station_save)
        self.station.pack(side='top', fill="both", expand=True)

        
        lensPositionLevel = 15
        lensPositionRange = np.arange(0, 255+(255/(lensPositionLevel-1)), 255/(lensPositionLevel-1)).tolist()
        self.focus_dict = dict([(str(level+1), int(value)) for (level,value) in enumerate(lensPositionRange)])
        self.focus_dict['AUTO'] = -1 # Autofocus
        
        focuslabel = Label(self, text="Focus Level: ")
        focuslabel.pack(side = "left")
        self.focus_dict_inv = {value:key for key, value in self.focus_dict.items()} # gets inverse
        self.focus_choices = list(self.focus_dict.keys())
        self.focus_choices.insert(0, self.focus_choices.pop(self.focus_choices.index('AUTO'))) # Move AUTO to index 0
        self.focus_var = StringVar(self)
        self.focus = OptionMenu(self, self.focus_var, *self.focus_choices, command=self.focus_save)
        self.focus.pack(side='top', fill="both", expand=True)

    def focus_load(self):
        """
            Loads the current focus based on self.name
        """
        focus_num = pickle_util.load(f"storage-oak/focus_{self.name}.pb", error_return = None)
        if focus_num == None or focus_num not in self.focus_dict_inv:
            self.focus_var.set('X')
        else:
            self.focus_var.set(self.focus_dict_inv[focus_num])

    def focus_save(self, *args):
        """
            Saves the current station based on self.name
        """
        log.info(f"Focus Level Selected for {self.name}: {self.focus_var.get()} -> {self.focus_dict[self.focus_var.get()]}")
        focus_num = self.focus_dict[self.focus_var.get()]
        pickle_util.save(f"storage-oak/focus_{self.name}.pb", focus_num)
        
        self.after(3*1000, self.set_view) # 3 second delay

    def station_load(self):
        """
            Loads the current station based on self.name
        """
        loop_num = pickle_util.load(f"storage-oak/station_{self.name}.pb", error_return = '255')
        if loop_num == '255':
            self.station_var.set('Select Station')
        else:
            self.station_var.set(self.station_dict[loop_num])

    def station_save(self, *args):
        """
            Saves the current station based on self.name
        """
        log.info(f"Station Selected for {self.name}: {self.station_var.get()}")
        loop_num = self.station_dict_inv[self.station_var.get()]
        pickle_util.save(f"storage-oak/station_{self.name}.pb", loop_num)

    def clear_all(self):
        """
            Removes the ROI for self.name and sets the view for self.name
        """
        self.clear_bbox()
        self.set_view()
        
    def set_title(self):
        """
            Sets the canvas title for self.name
        """
        self.title(f"Camera {self.name}")

    def set_view(self):
        """
            Sets the view and ROI for self.name
        """
        self.main.delete("all")
        self.load_imgfile(f'storage-oak/{self.name}.png')
        self.set_bbox()

    def next(self):
        """
            Updates the view to the next camera in self.cameralist
        """
        self.camerapointer = self.camerapointer + 1 if self.camerapointer < len(self.cameralist) - 1 else 0  
        self.name = self.cameralist[self.camerapointer]   
        self.refresh_gui()

    def prev(self):
        """
            Updates the view to the previous camera in self.cameralist
        """
        self.camerapointer = self.camerapointer - 1 if self.camerapointer > 0 else len(self.cameralist) - 1 
        self.name = self.cameralist[self.camerapointer]
        self.refresh_gui()
    
    def store_bbox(self, bbox):   
        """
            Sets the ROI for self.name and saves it in the pickled self.bboxhash
        """ 
        self.bboxhash[self.name] = [bbox] # for one roi only
        
        # selection for multiple ROI
        ### if self.name in self.bboxhash: 
        ###     self.bboxhash[self.name].append(bbox)
        ### else:
        ###    self.bboxhash[self.name] = [bbox]
        
        log.info(f"{self.name} ROI Store - {self.bboxhash[self.name]}")
        pickle_util.save(self.pickle_roi, self.bboxhash)
    
    def clear_bbox(self):
        """
            Removes the ROI for self.name
        """
        self.bboxhash[self.name] = []  
    
    def set_bbox(self):
        """
            Draws the ROI for self.name on the current view
        """
        if self.name in self.bboxhash:
            for bbox in self.bboxhash[self.name]:
                self.main.create_rectangle(bbox, outline="white", width = 3)          

    def load_imgfile(self, filename):
        """
            Loads the image from filename and sets it to be the current view
        """
        img = Image.open(filename)
        self.currentImage['data'] = img

        photo = ImageTk.PhotoImage(img)
        self.main.xview_moveto(0)
        self.main.yview_moveto(0)
        self.main.create_image(0, 0, image=photo, anchor='nw', tags='img')
        self.main.config(scrollregion=self.main.bbox('all'))
        self.currentImage['photo'] = photo

    def on_closing(self):
        """
            Destroys the tkinter application after performing a sanity check
            Sets pickled drawroi_running.pb to False to notify runoak.py
        """
        sanity_ok = self.sanity_check()
        if sanity_ok:
            log.info("Closing drawroi app")
            pickle_util.save("storage-oak/drawroi_running.pb", False)
            self.destroy()
    
    def sanity_check(self):
        """
            Checks each name in self.cameralist for an ROI and unique Station
        """
        log.info("Performing Sanity Check")
        sanity_ok = True
        error_str = ""
        # check if ROI drawn on all cameras
        for name in self.cameralist:
            if self.bboxhash[name] == []:
                error_str += f"No ROI on Camera {name}\n"
                sanity_ok = False
        
        # check if Station is Unique
        station_roundup = []
        for name in self.cameralist:
            loop_num = pickle_util.load(f"storage-oak/station_{name}.pb", error_return = '255')
            if loop_num == '255':
                error_str += f"No Station Selected on Camera {name}\n"
                sanity_ok = False
            elif loop_num in station_roundup and loop_num != '000':
                error_str += f"Duplicate Station {self.station_dict[loop_num]} on Camera {name}\n"
                sanity_ok = False
            else:
                station_roundup.append(loop_num)

        # check if focus is selected
        for name in self.cameralist:
            focus_num = pickle_util.load(f"storage-oak/focus_{name}.pb", error_return = None)
            if focus_num == None:
                error_str += f"No Focus Level Selected on Camera {name}\n"
                sanity_ok = False

        if not sanity_ok:
            tkinter.messagebox.showinfo("[ERROR]", error_str)
            log.error(error_str)

        return sanity_ok

    def on_mouse_down(self, event):
        """
            Updates self.anchor
        """        
        self.anchor = (event.widget.canvasx(event.x),
                       event.widget.canvasy(event.y))
        self.item = None
        
        self.can_refresh = False

    def on_mouse_drag(self, event):  
        """
            Draws Temporary ROI in yellow on current view when mouse is dragged
        """      
        bbox = self.anchor + (event.widget.canvasx(event.x),
                              event.widget.canvasy(event.y))
        if self.item is None:
            self.item = event.widget.create_rectangle(bbox, outline="yellow", width = 3)
        else:
            event.widget.coords(self.item, *bbox)

    def on_mouse_up(self, event):     
        """
            Stores drawn ROI coordinates and updates current view with new ROI
        """   
        if self.item:
            self.on_mouse_drag(event) 
            box = tuple((int(round(v)) for v in event.widget.coords(self.item)))

            roi = self.currentImage['data'].crop(box) # region of interest
            values = roi.getdata() # <----------------------- pixel values
            
            self.store_bbox(box)
            self.set_view()
        
        self.can_refresh = True

    def on_right_click(self, event):
        found = event.widget.find_all()
        for iid in found:
            if event.widget.type(iid) == 'rectangle':
                event.widget.delete(iid)


def refresh_view_on_interval():
    """
        Refreshes drawroi view on an interval
    """
    seconds_interval = 2
    if app.can_refresh:
        app.set_view()    
    app.after(seconds_interval*1000, refresh_view_on_interval)

def add_tkinter_display():
    """
       Add missing tkinter display parameter
       Without this GUI may not work on Ubuntu
    """
    if os.environ.get('DISPLAY','') == '':
        log.info(f'No display found for tkinter GUI. Using :0.0')
        os.environ.__setitem__('DISPLAY', ':0.0')

if __name__ == "__main__":
    log.info("Started drawroi Process")
    add_tkinter_display()
    pickle_util.save("storage-oak/drawroi_running.pb", True) # notifies runoak.py to save frames for tkinter view
    app =  MyApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    try:
        #log.info(f"Refreshing drawroi on Interval")
        #refresh_view_on_interval()
        app.mainloop()
    except KeyboardInterrupt:
        log.info(f"Keyboard Interrupt")
        app.on_closing()
