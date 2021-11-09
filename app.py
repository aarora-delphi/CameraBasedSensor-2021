#!/usr/bin/env python3

### python-packages
from flask import Flask, request, render_template, Response, flash, send_file, make_response, jsonify, redirect
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import numpy as np
import os
import base64

### local-packages
import pickle_util
from logger import *
from flask_controls import AppControls

# Main Flask used for routing.
app = Flask(__name__)

control = AppControls()

@app.route('/')
def show_stream():
    """
        Function called when Flask boots up for the first time.
    """

    # todo: set to False when done flask app is not running.
    pickle_util.save("storage-oak/drawroi_running.pb", True) # notifies runoak.py to save frames for flask view

    return render_template('show_stream.html', \
                cameralist = control.get_camera_choices(), \
                stationlist = control.get_station_choices(), \
                focuslist = control.get_focus_choices())

@app.route('/update_roi/<camera_id>', methods=['GET','POST'])
def update_roi(camera_id):
    """
        Function called when the user updates the ROI.
    """
    if request.method == 'GET':
        return control.get_roi(camera_id)
    elif request.method == 'POST':
        print(f"POST Request JSON: {request.json}")
        status = control.set_roi(camera_id, request.json['payload'])
        return jsonify({'status': status, 'roi': request.json['payload']})

@app.route('/update_view/<camera_id>', methods=['GET'])
def update_view(camera_id):
    """
    Returns the View for a Camera.
    If the View is Unavailable, a Blank Image is Returned
    """
    image_path = control.get_view(camera_id)

    with open(image_path, "rb") as f:
        image_binary = f.read()
        image = base64.b64encode(image_binary).decode("utf-8")
        return jsonify({'status': True, 'image': image})


@app.route('/update_station/<camera_id>', methods=['GET','POST'])
def update_station(camera_id):
    """
    Returns the Station for a Camera
    """
    if request.method == 'GET':
        return control.get_station(camera_id)
    elif request.method == 'POST':
        print(f"POST Request JSON: {request.json}")
        status = control.set_station(camera_id, request.json['payload'])
        return jsonify({'status': status, 'station': request.json['payload']})


@app.route('/update_focus/<camera_id>', methods=['GET','POST'])
def update_focus(camera_id):
    """
    Returns the Focus Level for a Camera
    """
    if request.method == 'GET':
        return control.get_focus(camera_id)
    elif request.method == 'POST':
        print(f"POST Request JSON: {request.json}")
        status = control.set_focus(camera_id, request.json['payload'])
        return jsonify({'status': status, 'focus': request.json['payload']})

if __name__ == "__main__":        
    app.run(host="0.0.0.0", port=2000,  debug=True)