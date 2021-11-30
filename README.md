Glossary of contents
	
	- requirements.txt: Contains all OS-packages and python packages needed to install
	
	- script/ubuntu_configure.sh: Shell Script to install the packages needed on the Zotac box

# CameraBasedSensor-2021

## How to do a Fresh Install on a New Ubuntu Server
1. Run script/ubuntu_configure.sh

## How to Run Camera Application:
1. Run gotocam # bash alias to set virtual environment and cd into correct folder
2. Run python3 runsim.py -full -track # runs OAK-1 Cameras with full 16:9 view and enables Insight Track Event Messaging
3. Run python3 app.py # runs Flask Configuration Application for setting ROI, station, and focus level
4. Note: These scripts will run on boot

## How to Set Camera Configurations:
1. Open http://0.0.0.0:2000/ on the LAN via desktop / mobile
2. Login to Flask Configuration Application
3. Now you can see live camera views and set the ROI, station, and focus level for each Camera
4. Note: Changing the station requires a reboot for changes to be administered.

## How to Set a Static IPv4 on a POE Device:
1. Run python3 script/bootloader/flash_bootloader.py # updates POE Camera bootloader to latest version 
2. Run python3 script/bootloader/bootloader_config.py flash # flashes POE Camera with base JSON configuration
3. Run python3 script/bootloader/set_ipv4.py # enter ipv4, mask, gateway here to flash onto bootloader

## How to fix a Softbricked OAK-1 POE Device:
1. Unplug Ethernet Cable
2. Unscrew and Open the OAK-1 POE Device Enclosure
3. Set the Boot Pins to USB Mode (Pins 2,4,5 are ON)
4. Plug Device via USB-C Cable
5. Run python3 script/bootloader/fix_softbrick.py
6. Unplug USB-C Cable
7. Set the Boot Pins to Flash Mode (Pins 5,6 are ON)
8. Plug Ethernet Cable
9. Check Device Connectivity
10. Screw Back and Close the OAK-1 POE Device Enclosure

## Other Information:
1. DepthAI Documentation: https://docs.luxonis.com/en/latest/
2. Luxonis Discussion Forum: https://discuss.luxonis.com/
3. OAK-1 POE Camera Listing: https://shop.luxonis.com/collections/all/products/oak-1-poe
