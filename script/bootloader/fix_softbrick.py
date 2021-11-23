import depthai as dai
import tempfile
​
blBinary = dai.DeviceBootloader.getEmbeddedBootloaderBinary(dai.DeviceBootloader.Type.NETWORK)
blBinary = blBinary + ([0xFF] * ((8 * 1024 * 1024 + 512) - len(blBinary)))
​
with tempfile.NamedTemporaryFile() as tmpBlFw:
    tmpBlFw.write(bytes(blBinary))
​
    (f, bl) = dai.DeviceBootloader.getFirstAvailableDevice()
    if not f:
        print('No devices found, exiting...')
        exit(-1)
​
    with dai.DeviceBootloader(bl) as bootloader:
        progress = lambda p : print(f'Flashing progress: {p*100:.1f}%')
        # Override SBR table, to prevent booting flashed application
        [success, msg] = bootloader.flashBootloader(progress, tmpBlFw.name)
        if success:
            print('Successfully overwritten SBR table. Device should be reacheable through PoE after switching the boot switches back to previous (0x3) value')
        else:
            print(f"Couldn't overwrite SBR table to unbrick the device. Error: {msg}")