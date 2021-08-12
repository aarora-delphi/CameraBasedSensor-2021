import cv2
import depthai as dai

pipeline = dai.Pipeline()

camRgb = pipeline.createColorCamera()

xoutRgb = pipeline.createXLinkOut()
xoutRgb.setStreamName("rgb")
camRgb.preview.link(xoutRgb.input)

device_info = dai.DeviceInfo()
device_info.state = dai.XLinkDeviceState.X_LINK_BOOTLOADER
device_info.desc.protocol = dai.XLinkProtocol.X_LINK_TCP_IP
device_info.desc.name = "169.254.1.222"

with dai.Device(pipeline, device_info) as device:
    qRgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
    while True:
        cv2.imshow("rgb", qRgb.get().getCvFrame())
        if cv2.waitKey(1) == ord('q'):
            break
