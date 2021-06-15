# Python-specific imports
from shapely.geometry import Polygon
import matplotlib.pyplot as plt

def intersection_of_polygons(ROI, BBOX, thresh=0.7, debug=False, showPlot=False, figure="1"):
	"""
		Measures the intersection of 2 polygons (ROI and BBOX) from their coordinates and determines whether the BBOX
		is within the ROI or not based on the intersection percentage relative to both the ROI and BBOX.
		ROI: list of [x,y] coordinates specifying Region on Interest
		BBOX: list of [x,y] coordinates specifying Bounding Box produced from YOLO model
		thresh: 0.0-1.0 threshold used to vary acceptance whether the BBOX is within the ROI or not
		debug: boolean - prints additional useful metrics such as intersection area and intersection percentage
		showPlot: boolean - shows the plot of ROI and BBOX and its intersection if present
		figure: name of the figure used in showPlot
		boolean - whether the BBOX is within the ROI or not
	"""


	ROI = Polygon([tuple(l) for l in ROI])
	BBOX = Polygon([tuple(l) for l in BBOX])
	INTERSECT = BBOX.intersection(ROI) # create polygon object made from intersection of ROI and BBOX

	isIntersect = BBOX.intersects(ROI) # boolean to determine if intersection is true

	if not isIntersect:
		#print("BBOX intersects ROI: {}".format(isIntersect))
		return False

	isIntersectArea = INTERSECT.area
	isIntersectPercentRelativeROI = INTERSECT.area/ROI.area # intersection percentage relative to ROI
	isIntersectPercentRelativeBBOX = INTERSECT.area/BBOX.area # intersection percentage relative to BBOX

	isIntersectCoord = [list(l) for l in list(INTERSECT.exterior.coords)] # intersection coordinates
	isVehicleCounted = isIntersectArea == ROI.area or isIntersectArea == BBOX.area \
						or isIntersectPercentRelativeBBOX > thresh \
						or isIntersectPercentRelativeROI > thresh # determine whether to count BBOX in ROI or not

	if debug:
		print("BBOX intersects ROI: {}".format(isIntersect))
		print("Area of intersection: {}".format(isIntersectArea))
		print("{:2f}% of BBOX intersects with ROI".format(isIntersectPercentRelativeBBOX * 100))
		print("{:2f}% of ROI intersects with BBOX".format(isIntersectPercentRelativeROI * 100))
		print("Intersection Coordinates: {}".format(isIntersectCoord))
		print("Vehicle is counted: {}".format(isVehicleCounted))
		print()

		if showPlot: # plot the graphs
			plt.plot(*ROI.exterior.xy, label="ROI", linewidth=4, color="magenta")
			plt.plot(*BBOX.exterior.xy, label="BBOX", linewidth=4, color="orange")
			if isIntersect:
				plt.plot(*INTERSECT.exterior.xy, label="INTERSECT", linewidth=2, color="blue")
			plt.title(
				"Figure {}, Intersect Threshold: {}, Vehicle Counted: {}".format(figure, thresh, isVehicleCounted))
			plt.legend()
			plt.show()

	return isVehicleCounted

def test():
	"""
		Test some BBOX and ROI values and view the graphs.
	"""

	BBOX = [[572, 109], [227, 127], [221, 330], [552, 412], [670, 246], [612, 142]]
	ROI = [[503, 201], [397, 197], [395, 280], [492, 280]]

	isAccepted = intersection_of_polygons(ROI, BBOX, figure="1")

	ROI = [[572, 109], [227, 127], [221, 330], [552, 412], [670, 246], [612, 142]]
	BBOX = [[503, 201], [397, 197], [395, 280], [492, 280]]

	isAccepted = intersection_of_polygons(ROI, BBOX, figure="2")

	BBOX = [[572, 109], [227, 127], [221, 330], [552, 412], [670, 246], [612, 142]]
	ROI = [[303, 201], [197, 197], [195, 280], [292, 280]]

	isAccepted = intersection_of_polygons(ROI, BBOX, figure="3")

	ROI = [[572, 109], [227, 127], [221, 330], [552, 412], [670, 246], [612, 142]]
	BBOX = [[303, 201], [197, 197], [195, 280], [292, 280]]

	isAccepted = intersection_of_polygons(ROI, BBOX, figure="4")

if __name__ == "__main__":
	test()
