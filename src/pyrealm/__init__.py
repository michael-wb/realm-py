import atexit
import ctypes

from os.path import exists
from typing import List

from .realm import Realm

_realm_lib = None
_opened_realms: List[Realm] = []
_lib_path: str = ""
_initialized: bool = False

# Initialize the realm library with the realm C shared library
def realm_init(path: str):
    global _initialized
    global _lib_path
    global _realm_lib
    if path:
        if not exists(path):
            raise ValueError(f"Could not find library: {path}")
        else:
            # Load the dynamic lib
            _realm_lib = ctypes.CDLL(path)
            _lib_path = str(path)
            _initialized = True
    else:
        raise ValueError("Library path cannot be empty")

def get_lib_path() -> str:
    return _lib_path

def is_initialized() -> bool:
    return _initialized

def num_realms() -> int:
    return len(_opened_realms)

def num_open_realms() -> int:
    return len([x for x in _opened_realms if not x.closed])

# Make sure all the open realms are closed when exiting
def close_realms():
    for realm in _opened_realms:
        if not realm.closed:
            realm.close()

atexit.register(close_realms)

# Reload all the open realms
def refresh_realms():
    for realm in _opened_realms:
        if not realm.closed:
            realm.refresh()
