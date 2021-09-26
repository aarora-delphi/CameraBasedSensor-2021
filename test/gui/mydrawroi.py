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
        
        self.button_print = Button(self.root, text = "Display points", command = self.print_points)
        self.button_print.pack(side="top", fill="both", expand=True)
        
        self.button_next = Button(self.root, text = "Next", command = self.next)
        self.button_next.pack(side=RIGHT, fill="both", expand=True)
        self.button_prev = Button(self.root, text = "Prev", command = self.prev)
        self.button_prev.pack(side=LEFT, fill="both", expand=True)
        
        self.button_save = Button(self.root, text = "Save", command = self.clear_all)
        self.button_save.pack(side="top", fill="both", expand=True)
        self.button_clear = Button(self.root, text = "Clear", command = self.clear_all)
        self.button_clear.pack(side=LEFT, fill="both", expand=True)
        
        #self.canvas.bind("<Motion>", self.tell_me_where_you_are)
        #self.canvas.bind("<B1-Motion>", self.draw_from_where_you_are)

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

    def set_title(self, name):
        self.root.title(f"Camera {name}")
    
    def clear_all(self):
        self.canvas.delete("all")

    def print_points(self):
        if self.points_recorded:
            self.points_recorded.pop()
            self.points_recorded.pop()
        self.canvas.create_line(self.points_recorded, fill = "yellow")
        self.points_recorded[:] = []

    def tell_me_where_you_are(self, event):
        self.previous_x = event.x
        self.previous_y = event.y

    def draw_from_where_you_are(self, event):
        if self.points_recorded:
            self.points_recorded.pop()
            self.points_recorded.pop()

        self.x = event.x
        self.y = event.y
        self.canvas.create_line(self.previous_x, self.previous_y, 
                                self.x, self.y,fill="yellow")
        self.points_recorded.append(self.previous_x)
        self.points_recorded.append(self.previous_y)
        self.points_recorded.append(self.x)     
        self.points_recorded.append(self.x)        
        self.previous_x = self.x
        self.previous_y = self.y
    
    def main_loop(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ExampleApp()
    app.main_loop()
