import tkinter as tk
from PIL import Image, ImageTk

import os

if os.environ.get('DISPLAY','') == '':
    print('no display found. Using :0.0')
    os.environ.__setitem__('DISPLAY', ':0.0')

WIDTH, HEIGHT = 900, 900
topx, topy, botx, boty = 0, 0, 0, 0
rect_id = None
path = "test.jpg"


def get_mouse_posn(event):
    global topy, topx

    topx, topy = event.x, event.y

def update_sel_rect(event):
    global rect_id
    global topy, topx, botx, boty

    botx, boty = event.x, event.y
    canvas.coords(rect_id, topx, topy, botx, boty)  # Update selection rect.


window = tk.Tk()
window.title("Select Area")
window.geometry('%sx%s' % (WIDTH, HEIGHT))
window.configure(background='grey')

img = ImageTk.PhotoImage(Image.open(path))
canvas = tk.Canvas(window, width=img.width(), height=img.height(),
                   borderwidth=0, highlightthickness=0)
canvas.pack(expand=True)
canvas.img = img  # Keep reference in case this code is put into a function.
canvas.create_image(0, 0, image=img, anchor=tk.NW)

# Create selection rectangle (invisible since corner points are equal).
rect_id = canvas.create_rectangle(topx, topy, topx, topy,
                                  dash=(2,2), fill='', outline='white')

canvas.bind('<Button-1>', get_mouse_posn)
canvas.bind('<B1-Motion>', update_sel_rect)

window.mainloop()
