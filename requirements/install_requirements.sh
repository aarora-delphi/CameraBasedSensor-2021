#!/bin/bash

echo "INSTALLING WITH PACKAGE MANAGER"
sudo apt-get install python3.6

echo "INSTALLING PYTHON DEPENDENCIES"
pip3 install flask
pip3 install numpy
pip3 install opencv-python
pip3 install shapely
pip3 install matplotlib
pip3 install imutils 
pip3 install pillow
pip3 install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp36-cp36m-linux_x86_64.whl




echo "INSTALLATION COMPLETE"

