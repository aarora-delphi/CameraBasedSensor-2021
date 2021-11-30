### python-packages
import pickle
import fcntl
import configparser

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

def getconfig(section, key, value, error_return = None):
    """
        Gets the value of the key from the config file
    """
    config = configparser.ConfigParser(inline_comment_prefixes="#")
    config.read('storage-oak/properties.ini')
    
    try:
        if value == 'int':
            result = config.getint(section, key)
        elif value == 'float':
            result = config.getfloat(section, key)
        elif value == 'bool':
            result = config.getboolean(section, key)
        elif value == 'str':
            result = config.get(section, key)
        else:
            log.warning(f"INVALID CONFIG TYPE for {section} {key} - Returning default {error_return}")
            return error_return
        
        log.info(f"FOUND CONFIG {section}.{key}.{value} = {result}")
        return result

    except:
        log.error(f"FAILED TO GET CONFIG {section}.{key}.{value} - Returning default {error_return}")
        return error_return