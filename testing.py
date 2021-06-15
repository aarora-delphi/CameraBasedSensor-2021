import unittest
from camera import Camera

class CameraTests(unittest.TestCase):
	def test_camera(self):
		self.camera = Camera(0)
		self.assertFalse(self.camera.VS.read() is None)

	def test(self):
		self.assertEqual(1,1)
	
if __name__ == "__main__":
	unittest.main()
