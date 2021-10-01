### python-packages
import pickle
import fcntl

### local-packages
from logger import *


def acquireLock():
    ''' acquire exclusive lock file access '''
    locked_file_descriptor = open('storage-oak/lockfile.LOCK', 'w+')
    fcntl.lockf(locked_file_descriptor, fcntl.LOCK_EX)
    return locked_file_descriptor

def releaseLock(locked_file_descriptor):
    ''' release exclusive lock file access '''
    locked_file_descriptor.close()

# TO DO - lock save() on file by file basis
### lock_fd = acquireLock()
### ... do stuff with exclusive access to your file(s)
### releaseLock(lock_fd)

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
