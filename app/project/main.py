# main.py

### python-packages
from flask import Blueprint, render_template, Flask, request, render_template, Response, flash, send_file, make_response, jsonify, redirect
from flask_login import login_required, current_user
import base64
import redis

### local-packages
from project.utilities.flask_controls import AppControls

r = redis.StrictRedis()
control = AppControls()
main = Blueprint('main', __name__)


@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.username)

@main.route('/')
@login_required
def index():
    """
        Function called when Flask boots up for the first time.
    """

    # todo: set to False when done flask app is not running.
    control.set_app_active(True)

    return render_template('show_stream.html', \
                cameralist = control.get_camera_choices(), \
                stationlist = control.get_station_choices(), \
                focuslist = control.get_focus_choices())

@main.route('/update_roi/<camera_id>', methods=['GET','POST'])
@login_required
def update_roi(camera_id):
    """
        Function called when the user updates the ROI.
    """
    if request.method == 'GET':
        x1, y1, x2, y2 = control.get_roi(camera_id)
        return jsonify({'status': True, 'x': x1, 'y': y1, 'width': x2-x1, 'height': y2-y1})
    
    elif request.method == 'POST':
        print(f"POST Request JSON: {request.json}")
        status = control.set_roi(camera_id, tuple(request.json['payload']))
        return jsonify({'status': status, 'roi': request.json['payload']})

@main.route('/update_view/<camera_id>', methods=['GET'])
@login_required
def update_view(camera_id):
    """
    Returns the View for a Camera.
    If the View is Unavailable, a Blank Image is Returned
    """
    img_bytes_ = r.get(camera_id)
    if img_bytes_ is not None:
        decoded = base64.b64encode(img_bytes_).decode("utf-8")
        return jsonify({'status': True, 'image': decoded})

    image_path = control.get_view(camera_id)
    with open(image_path, "rb") as f:
        image_binary = f.read()
        image = base64.b64encode(image_binary).decode("utf-8")
        return jsonify({'status': True, 'image': image})

@main.route('/update_station/<camera_id>', methods=['GET','POST'])
@login_required
def update_station(camera_id):
    """
    Returns the Station for a Camera
    """
    if request.method == 'GET':
        return jsonify({'status': True, 'data': control.get_station(camera_id)})
    
    elif request.method == 'POST':
        print(f"POST Request JSON: {request.json}")
        status = control.set_station(camera_id, request.json['payload'])
        return jsonify({'status': status, 'station': request.json['payload']})

@main.route('/update_focus/<camera_id>', methods=['GET','POST'])
@login_required
def update_focus(camera_id):
    """
    Returns the Focus Level for a Camera
    """
    if request.method == 'GET':
        return jsonify({'status': True, 'data': control.get_focus(camera_id)})
    
    elif request.method == 'POST':
        print(f"POST Request JSON: {request.json}")
        status = control.set_focus(camera_id, request.json['payload'])
        return jsonify({'status': status, 'focus': request.json['payload']})