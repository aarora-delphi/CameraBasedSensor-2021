### python-packages
import pickle
import fcntl

### local-packages
from project.utilities.logger import *

def save(file_name, obj):
    
    with open(file_name, 'wb') as fobj:
        pickle.dump(obj, fobj)

def load(file_name, error_return = None):
    try:
        with open(file_name, 'rb') as fobj:
            return pickle.load(fobj)
    except:
        log.info(f"Failed to Load {file_name}")
        return error_return
