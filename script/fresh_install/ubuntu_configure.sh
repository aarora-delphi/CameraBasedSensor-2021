#!/bin/bash

### UBUNTU LIBRARY INSTALLATIONS

sudo apt update
sudo apt install -y vim
sudo apt install -y git
sudo apt install -y curl
sudo apt install -y xdotool
sudo apt-get install -y wmctrl

# ssh on port 22
sudo apt-get install openssh-server

# test - remove kernel error with python 3.6
sudo apt-get --only-upgrade install unattended-upgrades

### UBUNTU FIREWALL CONFIGURATION

sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 5000
sudo ufw allow 11490/tcp
sudo ufw allow 11491/udp
sudo ufw allow 1024:65535/udp
sudo ufw allow 5938/udp
sudo ufw allow 5938/tcp
sudo ufw allow 2000

### PYTHON3.9 INSTALLATION

sudo apt install -y wget build-essential checkinstall
sudo apt install -y libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev

cd /opt
sudo wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz
sudo tar xzf Python-3.9.7.tgz
cd Python-3.9.7/
sudo ./configure --enable-optimizations
sudo make altinstall
cd ..
python3.9 -V
sudo rm -f Python-3.9.7.tgz
cd ~

### ALIAS SETUP

grep -qxF "alias d='deactivate'" ~/.bash_aliases || echo "alias d='deactivate'" >> ~/.bash_aliases
grep -qxF "alias s='source venv/bin/activate'" ~/.bash_aliases || echo "alias s='source venv/bin/activate'" >> ~/.bash_aliases
grep -qxF "alias gotocam='cd ~/Desktop/CameraBasedSensor-2021; s'" ~/.bash_aliases || echo "alias gotocam='cd ~/Desktop/CameraBasedSensor-2021; s'" >> ~/.bash_aliases

source ~/.bashrc

### Python Repo Installation
cd ~/Desktop
git clone https://github.com/aarora-delphi/CameraBasedSensor-2021.git
git clone https://github.com/luxonis/depthai-python.git

### Python Virtual Environment Setup
cd ~/Desktop/CameraBasedSensor-2021
git checkout oak
python3.9 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate
# sudo cp ~/Desktop/CameraBasedSensor-2021 /opt

cd ~/Desktop/depthai-python
python3.9 -m venv venv
source venv/bin/activate
cd examples
python3 install_requirements.py
deactivate
# sudo cp ~/Desktop/depthai-python /opt

### UBUNTU STARTUP MANAGER
cd ~/Desktop/CameraBasedSensor-2021/script/fresh_install

# copy files to startup manager if not exists - source -> destination
mkdir ~/.config/autostart
cp ./boot_hook.sh.desktop ~/.config/autostart/boot_hook.sh.desktop
cp ./firefox.desktop ~/.config/autostart/firefox.desktop

### Redis Server Installation
sudo apt install -y redis-server

### GNOME CONFIGURATIONS

# show ubuntu clock seconds
gsettings set org.gnome.desktop.interface clock-show-seconds true

# set ubuntu screen recording to 1 hour
gsettings set org.gnome.settings-daemon.plugins.media-keys max-screencast-length 3600

# set desktop background to black
gsettings set org.gnome.desktop.background picture-uri ""
gsettings set org.gnome.desktop.background primary-color '#000000'
gsettings set org.gnome.desktop.background color-shading-type 'solid'

# disable lock screen
gsettings set org.gnome.desktop.lockdown disable-lock-screen 'true'

# disable screen saver locking
gsettings set org.gnome.desktop.screensaver lock-enabled false

# disable bluetooth
sudo systemctl disable bluetooth.service

# disable apport error reporting
sudo systemctl disable apport

# disable dim screen when inactive in power settings
gsettings set org.gnome.settings-daemon.plugins.power idle-dim false

# disable blank screen in power settings
gsettings set org.gnome.desktop.session idle-delay 0
