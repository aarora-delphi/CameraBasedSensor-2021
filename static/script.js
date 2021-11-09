var completed = false;
var dragging = false;
var drawing = false;
var startPoint;
var allCircles = [];

// svg tag holds the stream and draggable ROI
var svg = d3.select('body').append('svg')
.attr('height', 450)
.attr('width', 800)
.attr('style', 'background: url("/stream_feed")');

var points = [], g;

var dragger = d3.behavior.drag()
    .on('drag', handleDrag)
    .on('dragend', function(d){
        var polygon = d3.select('polygon');
        var points = polygon.attr('points');
        console.log("Polygon points: ", points);
        sendROI(points.split(",").map(num => parseFloat(num)))
        dragging = false;
    });

// when mouse is up, point on ROI is created and line is drawn to connect to new point
svg.on('mouseup', function(){
    console.log("mouse up svg");
    if (dragging) {
        return;
    }
    if (completed) {
        return;
    }
    drawing = true;
    startPoint = [d3.mouse(this)[0], d3.mouse(this)[1]];
    
    if(svg.select('g.drawPoly').empty()){
        g = svg.append('g').attr('class','drawPoly');
    }

    if(d3.event.target.hasAttribute('is-handle')){
        closePolygon();
        return;
    }

    points.push(d3.mouse(this));
    g.select('polyline').remove();

    var polyline = g.append('polyline').attr('points', points).style('fill', 'none').attr('stroke','#49fb35').attr('stroke-width', 2);

    // Adding circles for each point in the points list
    for(var i = 0; i < points.length; i++){
        g.append('circle')
        .attr('cx', points[i][0])
        .attr('cy', points[i][1])
        .attr('r', 10)
        .attr('fill','#49fb35')
        .attr('stroke', '#000')
        .attr('is-handle', 'true')
        .style({cursor: 'pointer'});
    }
});

// mouse move function
svg.on('mousemove', function() {
    console.log("mousemove function");
    if(!drawing) return;
    var g = d3.select('g.drawPoly');
    g.select('line').remove();
    var line = g.append('line')
                .attr('x1', startPoint[0])
                .attr('y1', startPoint[1])
                .attr('x2', d3.mouse(this)[0] + 2)
                .attr('y2', d3.mouse(this)[1])
                .attr('stroke', '#49fb35')
                .attr('stroke-width', 3);
})

// once a polygon is created on the frontend, close the polygon shape with opacity
function closePolygon(){
    console.log("closePolygon func");
    svg.select('g.drawPoly').remove();
    var g= svg.append('g');
    g.append('polygon')
    .attr('points', points)
    .attr("opacity", ".2")
    .attr('stroke', '#000')
    .attr('stroke-opacity', "1")
    .attr('stroke-width', 5)
    .style('fill', getColor());

    current_points = []
    for (var i = 0; i < points.length; i++){
        current_points.push(points[i][0]); // this will log x points
        current_points.push(points[i][1]); // this will log y points
        
        var circle = g.selectAll('circles')
        .data([points[i]])
        .enter()
        .append('circle')
        .attr('cx', points[i][0])
        .attr('cy', points[i][1])
        .attr('r', 10)
        .attr('fill', 'green')
        .attr('stroke', '#000')
        .attr('is-handle', 'true')
        .style({cursor: 'move'})
        .call(dragger);

        console.log("CIRCLE:", circle.attr('cx'));
    }
    console.log("CURRENTPOINTS: ", current_points);
    sendROI(current_points);      // send points to backend once polygon is closed
    points.splice(0);
    drawing = false;
    completed = true;             // made this true keeping this true to prevent drawing once filled until user clears
}

// allows corners of ROI to be dragged on frontend
function handleDrag() {
    console.log("handleDrag function");
    if(drawing) return;
    var dragCircle = d3.select(this), newPoints = [], circle;
    dragging = true;
    var poly = d3.select(this.parentNode).select('polygon');
    var circles = d3.select(this.parentNode).selectAll('circle');
    dragCircle
    .attr('cx', d3.event.x)
    .attr('cy', d3.event.y);
    for (var i = 0; i < circles[0].length; i++) {
        circle = d3.select(circles[0][i]);
        newPoints.push([circle.attr('cx'), circle.attr('cy')]);
    }
    poly.attr('points', newPoints);
}

// neon green color for ROI lines and points
function getColor() {
    return '#49fb35';
}

// sends ROI points to the backend
function sendROI(points){
    console.log("sendROI POINTS RECEIVED:", points);
    var sendPoints = [];
    
    for (var i = 0; i < points.length; i+=2){
        sendPoints.push({x: Math.round(points[i]), y: Math.round(points[i+1])});
    	}

	console.log("SENDING POINTS TO BACKEND", sendPoints);

    $.post("/record_roi",
    {
        roi_coord: sendPoints
    });  
}

// removes ROI drawn from frontend
function removeROI(){
		console.log("REMOVE CLICKED")
		svg.selectAll('*').remove();
		completed = false;
	}

// draws existing ROI if available from backend
function cameraSwitchOnReload(points){
    console.log("CAMERA SWITCH TRIGGERED");
    svg.select('g.drawPoly').remove();
    var g= svg.append('g');
    g.append('polygon')
    .attr('points', points)
    .attr("opacity", ".2")
    .attr('stroke', '#000')
    .attr('stroke-opacity', "1")
    .attr('stroke-width', 5)
    .style('fill', getColor());

    current_points = []
    for (var i = 0; i < points.length; i++){
        current_points.push(points[i]);
        var circle = g.selectAll('circles')
        .data([points[i]])
        .enter()
        .append('circle')
        .attr('cx', points[i][0])
        .attr('cy', points[i][1])
        .attr('r', 10)
        .attr('fill', 'green')
        .attr('stroke', '#000')
        .attr('is-handle', 'true')
        .style({cursor: 'move'})
        .call(dragger);

        console.log("CIRCLE:", circle.attr('cx'));
    }
    
    sendROI(current_points);      // send points to backend once polygon is closed
    points.splice(0);
    drawing = false;
    completed = true;             //made this true keeping this true to prevent drawing once filled until user clears
}
