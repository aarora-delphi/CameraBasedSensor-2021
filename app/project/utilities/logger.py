### python-packages
import logging
from datetime import date
import sys
from pathlib import Path
import os

logtoconsole = True
dir_path = os.path.dirname(os.path.abspath(__file__))
logfile = f'{dir_path}/../../../log/{date.today()}.log'

# create file if file does not exist
Path(logfile).touch(exist_ok=True)

# create and configure logger
logging.basicConfig(filename = logfile,
                    format='%(asctime)s.%(msecs)03d [%(filename)-15.15s:%(lineno)-3.3d] [%(levelname)-4.4s] %(message)s',
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level = logging.INFO,
                    filemode='a')
  
# create handler to log to stdout
if logtoconsole:
    streamFormatter = logging.Formatter('[%(levelname)-4.4s] %(message)s')
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(streamFormatter)
    logging.getLogger().addHandler(streamHandler)

log=logging.getLogger()

if __name__ == "__main__":
    # test messages
    log.debug(f"Test - Harmless debug Message {logtoconsole}")
    log.info("Test - Just an information")
    log.warning("Test - Its a Warning")
    log.error("Test - Did you try to divide by zero")
    log.critical("Test - Internet is down")
