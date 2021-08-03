from tkinter import *
from PIL import ImageTk, Image


class ExampleApp():
    def __init__(self):
        self.root = Tk()
        self.previous_x = 0
        self.previous_y = 0
        self.x = 0
        self.y = 0
        self.points_recorded = []
        
        self.cameralist = ["A","B","C"]
        self.camerapointer = 0
        
        self.canvas = Canvas(self.root, width=400, height=400, bg = "white", cursor="cross")
        self.canvas.pack(side="top", fill="both", expand=True)
        
        self.set_view(self.cameralist[self.camerapointer])
        self.set_title(self.cameralist[self.camerapointer])
        
        self.button_print = Button(self.root, text = "Display points", command = self.clear_all)
        self.button_print.pack(side="top", fill="both", expand=True)
        
        self.button_next = Button(self.root, text = "Next", command = self.next)
        self.button_next.pack(side=RIGHT, fill="both", expand=True)
        self.button_prev = Button(self.root, text = "Prev", command = self.prev)
        self.button_prev.pack(side=LEFT, fill="both", expand=True)
        
        self.button_save = Button(self.root, text = "Save", command = self.clear_all)
        self.button_save.pack(side="top", fill="both", expand=True)
        self.button_clear = Button(self.root, text = "Clear", command = self.clear_all)
        self.button_clear.pack(side=LEFT, fill="both", expand=True)

        #img = ImageTk.PhotoImage(Image.open("cameraA.png"))  # PIL solution
        #self.canvas.create_image(20, 20, anchor=NW, image=img)

        mainloop()
        

    def clear_all(self):
        self.canvas.delete("all")
  
    def next(self):
        self.camerapointer = self.camerapointer + 1 if self.camerapointer < len(self.cameralist) - 1 else 0        
        name = self.cameralist[self.camerapointer]
        self.set_view(name)
        self.set_title(name)

    def prev(self):
        self.camerapointer = self.camerapointer - 1 if self.camerapointer > 0 else len(self.cameralist) - 1 
        name = self.cameralist[self.camerapointer] 
        self.set_view(name)
        self.set_title(name)  
        
    def set_view(self, name):
        img = ImageTk.PhotoImage(Image.open(f"camera{name}.png"))  # PIL solution
        print(img)
        self.canvas.create_image(20, 20, anchor=NW, image=img)
        #photo = tk.PhotoImage(file=f'camera{name}.png')
        #self.canvas.create_image(0,0, image=photo, anchor=NW)
        self.canvas.update()

    def set_title(self, name):
        self.root.title(f"Camera {name}")


if __name__ == "__main__":
    app = ExampleApp()
