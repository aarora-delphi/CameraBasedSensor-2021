from tkinter import *
from PIL import Image, ImageTk
import depthai as dai

import pickle_util

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
        #self.main = ScrolledCanvas(self)
        #self.main.grid(row=0, column=0, sticky='nsew')
        #self.c = self.main.canv
        self.c = self.main

        #self.cameralist = ["A","B","C"]
        self.cameralist = pickle_util.load("storage-oak/device_id.pb", error_return = ["A", "B", "C"])
        print(self.cameralist)
        
        self.camerapointer = 0
        self.name = self.cameralist[self.camerapointer]
        
        self.pickle_roi = "storage-oak/canvas_roi.pb"
        self.bboxhash = pickle_util.load(self.pickle_roi, error_return = {})
        
        self.currentImage = {}
        self.set_view()
        self.set_title()
        
        self.button_next = Button(self, text = "Next", command = self.next)
        self.button_next.pack(side=RIGHT, fill="both", expand=True)
        self.button_prev = Button(self, text = "Prev", command = self.prev)
        self.button_prev.pack(side=LEFT, fill="both", expand=True)
        
        self.button_save = Button(self, text = "Refresh", command = self.set_view)
        self.button_save.pack(side="top", fill="both", expand=True)
        self.button_clear = Button(self, text = "Clear", command = self.clear_all)
        self.button_clear.pack(side=LEFT, fill="both", expand=True)

        self.c.bind('<ButtonPress-1>', self.on_mouse_down)
        self.c.bind('<B1-Motion>', self.on_mouse_drag)
        self.c.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.c.bind('<Button-3>', self.on_right_click)

    def clear_all(self):
        # self.main.delete("all")
        self.clear_bbox()
        self.set_view()
        
    def set_title(self):
        self.title(f"Camera {self.name}")

    def set_view(self):
        self.main.delete("all")
        self.load_imgfile(f'storage-oak/{self.name}.png')
        self.set_bbox()

    def next(self):
        self.camerapointer = self.camerapointer + 1 if self.camerapointer < len(self.cameralist) - 1 else 0  
        self.name = self.cameralist[self.camerapointer]   
        self.set_view()
        self.set_title()

    def prev(self):
        self.camerapointer = self.camerapointer - 1 if self.camerapointer > 0 else len(self.cameralist) - 1 
        self.name = self.cameralist[self.camerapointer]
        self.set_view()
        self.set_title()
    
    def store_bbox(self, bbox):
        print("BBOX", bbox)
    
        self.bboxhash[self.name] = [bbox] # for one roi only
        #if self.name in self.bboxhash:
        #    self.bboxhash[self.name].append(bbox)
        #else:
        #    self.bboxhash[self.name] = [bbox]
        
        print("STORE", self.bboxhash[self.name])
        pickle_util.save(self.pickle_roi, self.bboxhash)
    
    def clear_bbox(self):
        self.bboxhash[self.name] = []  
    
    def set_bbox(self):
        if self.name in self.bboxhash:
            for bbox in self.bboxhash[self.name]:
                self.c.create_rectangle(bbox, outline="white", width = 3)          

    def load_imgfile(self, filename):
        
        img = Image.open(filename)
        # img = img.convert('L')
        self.currentImage['data'] = img

        photo = ImageTk.PhotoImage(img)
        self.c.xview_moveto(0)
        self.c.yview_moveto(0)
        self.c.create_image(0, 0, image=photo, anchor='nw', tags='img')
        self.c.config(scrollregion=self.c.bbox('all'))
        self.currentImage['photo'] = photo

    def on_closing(self):
        print("[INFO] Closing drawroi app")
        pickle_util.save("storage-oak/drawroi_running.pb", False)
        self.destroy()

    def on_mouse_down(self, event):        
        self.anchor = (event.widget.canvasx(event.x),
                       event.widget.canvasy(event.y))
        self.item = None

    def on_mouse_drag(self, event):        
        bbox = self.anchor + (event.widget.canvasx(event.x),
                              event.widget.canvasy(event.y))
        if self.item is None:
            self.item = event.widget.create_rectangle(bbox, outline="yellow", width = 3)
        else:
            event.widget.coords(self.item, *bbox)

    def on_mouse_up(self, event):        
        if self.item:
            self.on_mouse_drag(event) 
            box = tuple((int(round(v)) for v in event.widget.coords(self.item)))

            roi = self.currentImage['data'].crop(box) # region of interest
            values = roi.getdata() # <----------------------- pixel values
            print(roi.size, len(values))
            #print list(values)
            
            self.store_bbox(box)
            self.set_view()

    def on_right_click(self, event):        
        found = event.widget.find_all()
        for iid in found:
            if event.widget.type(iid) == 'rectangle':
                event.widget.delete(iid)



pickle_util.save("storage-oak/drawroi_running.pb", True)
app =  MyApp()
app.protocol("WM_DELETE_WINDOW", app.on_closing)

try:
    app.mainloop()
except KeyboardInterrupt:
    print(f"[INFO] Keyboard Interrupt")
    app.on_closing()
