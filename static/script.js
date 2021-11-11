
// get methods from server
function update_select(endpoint, select_element, notsetname) {

    fetch(endpoint)
        .then(response => response.json())
        .then(result => {
            console.log("GET: " + endpoint);
            console.log("Found: " + result['status']);

            // update the select element
            var object = result['data'];
            if (object == notsetname) {
                var opt = document.createElement('option');
                opt.id = object;
                opt.innerHTML = object;
                select_element.appendChild(opt);
            }
            select_element.options.namedItem(object).selected = true;
        })
}

function update_view(endpoint, view_element) {

    fetch(endpoint)
        .then(response => response.json())
        .then(result => {
            console.log("GET: " + endpoint);
            console.log("Found: " + result['status']);

            // Update the view
            view_element.src = 'data:;base64,' + result['image'];
        })
}

function update_roi(endpoint, roi_element) {

    fetch(endpoint)
        .then(response => response.json())
        .then(result => {
            console.log("GET: " + endpoint);
            console.log("Found: " + result['status']);

            // update the roi
            var ctx = roi_element.getContext('2d');
            ctx.clearRect(0, 0, roi_element.width, roi_element.height);
            ctx.strokeRect(result['x'], result['y'], result['width'], result['height']);
        })
}

function shortcut_update_station(camera_id) {
    update_select(endpoint = "/update_station/" + camera_id,
        select_element = document.getElementById("station_" + camera_id),
        notsetname = "Select Station");
}

function shortcut_update_focus(camera_id) {
    update_select(endpoint = "/update_focus/" + camera_id,
        select_element = document.getElementById("focus_" + camera_id),
        notsetname = "X");
}

function shortcut_update_view(camera_id) {
    update_view(endpoint = "/update_view/" + camera_id,
        view_element = document.getElementById("view_" + camera_id));
}

function shortcut_update_roi(camera_id) {
    update_roi(endpoint = "/update_roi/" + camera_id,
        roi_element = document.getElementById("roi_" + camera_id));
}

// set methods to server
function set_json(endpoint, payload) {

    fetch(endpoint, {
        method: 'post',
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 'payload': payload })
    }).then(res => res.json())
        .then(res => console.log(res));
}

function set_station(camera_id) {
    var select_element = document.getElementById("station_" + camera_id);
    var id = $(select_element).children(":selected").attr("id");

    set_json(endpoint = "/update_station/" + camera_id,
        payload = id);
}

function set_focus(camera_id) {
    var select_element = document.getElementById("focus_" + camera_id);
    var id = $(select_element).children(":selected").attr("id");

    set_json(endpoint = "/update_focus/" + camera_id,
        payload = id);
}

function set_roi(camera_id, roi) {
    set_json(endpoint = "/update_roi/" + camera_id,
        payload = roi);
}

// canvas related functions
function init_canvas(camera_id) {
    var canvas = get_canvas(camera_id);
    canvas.width = 300;
    canvas.height = 300;
    return canvas;
}

function get_canvas(camera_id) {
    return document.getElementById("roi_" + camera_id);
}

function draw_random(camera_id) {
    var canvas = get_canvas(camera_id);
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "red";
    ctx.fillRect(160, 240, 20, 20);
    ctx.fillText("Im on top of the world!", 30, 30);
}

function clear_roi(camera_id) {
    var canvas = get_canvas(camera_id);
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    console.log("Cleared ROI for " + camera_id)
}

// enables roi drawing on canvas
function roi_listener(camera_id) {

    // escape periods in camera_id with 2 backslashes
    var roi_id = "#roi_" + camera_id.replace(/\./g, "\\.");

    // get references to the canvas and context
    var canvas = init_canvas(camera_id);
    var ctx = canvas.getContext("2d");

    // style the context
    ctx.strokeStyle = "blue";
    ctx.lineWidth = 3;

    // this flag is true when the user is dragging the mouse
    var isDown = false;

    // these vars will hold the starting mouse position
    var startX;
    var startY;

    // calculate where the canvas is on the window
    // (used to help calculate mouseX/mouseY)
    var canvasOffset;
    var offsetX;
    var offsetY;
    recalculate_offsets();

    // add a scroll and resize listener to the window
    window.addEventListener("scroll", function (event) {
        recalculate_offsets();
    });
    window.addEventListener("resize", function (event) {
        recalculate_offsets();
    });

    // ensures drawn roi is relative to the canvas
    function recalculate_offsets() {
        canvasOffset = canvas.getBoundingClientRect();
        offsetX = canvasOffset.left;
        offsetY = canvasOffset.top;
        // console.log(camera_id + " offsetXY: " + offsetX + "," + offsetY);
    }

    // calculate corners of rectangle given two diagonal points
    function getTLBRCornersList(x1, y1, x2, y2) {
        var corners = {};
        corners.topLeft = {
            x: Math.min(x1, x2),
            y: Math.min(y1, y2)
        };
        corners.bottomRight = {
            x: Math.max(x1, x2),
            y: Math.max(y1, y2)
        };
        return [corners.topLeft.x, corners.topLeft.y, corners.bottomRight.x, corners.bottomRight.y];
    }

    function handleMouseDown(e) {
        e.preventDefault();
        e.stopPropagation();

        // save the starting x/y of the rectangle
        startX = parseInt(e.clientX - offsetX);
        startY = parseInt(e.clientY - offsetY);

        // set a flag indicating the drag has begun
        isDown = true;
    }

    function handleMouseUp(e) {
        e.preventDefault();
        e.stopPropagation();

        // the drag is over, clear the dragging flag
        isDown = false;
    }

    function handleMouseOut(e) {
        e.preventDefault();
        e.stopPropagation();

        // the drag is over, clear the dragging flag
        isDown = false;
    }

    function handleMouseMove(e) {
        e.preventDefault();
        e.stopPropagation();

        // if we're not dragging, just return
        if (!isDown) {
            return;
        }

        // get the current mouse position
        mouseX = parseInt(e.clientX - offsetX);
        mouseY = parseInt(e.clientY - offsetY);
        // console.log(camera_id + " startXY mouseXY: " + startX + " " + startY + " " + mouseX + " " + mouseY);

        // Put your mousemove stuff here

        // clear the canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // calculate the rectangle width/height based
        // on starting vs current mouse position
        var width = mouseX - startX;
        var height = mouseY - startY;

        // draw a new rect from the start position 
        // to the current mouse position
        ctx.strokeRect(startX, startY, width, height);

    }

    // listen for mouse events
    $(roi_id).mousedown(function (e) {
        handleMouseDown(e);
    });
    $(roi_id).mousemove(function (e) {
        handleMouseMove(e);
    });
    $(roi_id).mouseup(function (e) {
        handleMouseUp(e);
        set_roi(camera_id, getTLBRCornersList(startX, startY, mouseX, mouseY));
    });
    $(roi_id).mouseout(function (e) {
        handleMouseOut(e);
    });

}