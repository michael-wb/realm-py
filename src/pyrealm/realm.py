import ctypes
import os
import threading

from enum import Enum
from typing import (List, Tuple)

import pyrealm

from .config import RealmConfig
from .error import (RealmException, throw_last_error,)
from .property import (RealmPropertyInfo)
from .schema import (RealmClassInfo, RealmObject)


class RealmVersion():

    def __init__(self, version_string: str, major: int, minor: int, patch: int, extra: str):
        self.string = version_string
        self.major = major
        self.minor = minor
        self.patch = patch
        self.extra = extra

    def __str__(self):
        version_str = ""
        if self.string:
            version_str = self.string
        if self.major != 0 or self.minor != 0 or self.patch != 0:
            version_str += f" ({self.major}.{self.minor}.{self.patch}{'-' + self.extra if self.extra else ''})"
        return version_str


class Realm():

    class _RealmObject(ctypes.Structure):
        pass

    class _RealmVersionId(ctypes.Structure):
        _fields_ = [
            ("version", ctypes.c_uint64),
            ("index", ctypes.c_uint64),
        ]

    class _TransactionType(Enum):
        NONE = 0
        READ = 1
        WRITE = 2

    def __init__(self, config: RealmConfig):
        if config is None:
            raise ValueError("config cannot be None")

        self._init_if()
        self._transaction = Realm._TransactionType.NONE
        self._lock = threading.Lock()
        self._realm = self._open(config._config)
        if self._realm is None:
            throw_last_error("Error opening Realm object")
        pyrealm._opened_realms.append(self)
        self._config = config
        self._active_schema = None
        self._last_schema_version = None

    def _init_if(self):
        # Set up the interface for the Realm realm functions
        self._get_version_id = pyrealm._realm_lib.realm_get_version_id
        self._get_version_id.restype = ctypes.c_bool
        self._get_num_versions = pyrealm._realm_lib.realm_get_num_versions
        self._get_num_versions.restype = ctypes.c_bool
        self._open = pyrealm._realm_lib.realm_open
        self._open.restype = ctypes.POINTER(Realm._RealmObject)
        self._convert_with_config = pyrealm._realm_lib.realm_convert_with_config
        self._convert_with_config.restype = ctypes.c_bool
        self._convert_with_path = pyrealm._realm_lib.realm_convert_with_path
        self._convert_with_path.restype = ctypes.c_bool
        self._delete_files = pyrealm._realm_lib.realm_delete_files
        self._delete_files.restype = ctypes.c_bool
        self._is_closed = pyrealm._realm_lib.realm_is_closed
        self._is_closed.restype = ctypes.c_bool
        self._is_writable = pyrealm._realm_lib.realm_is_writable
        self._is_writable.restype = ctypes.c_bool
        self._close = pyrealm._realm_lib.realm_close
        self._close.restype = ctypes.c_bool
        self._begin_read = pyrealm._realm_lib.realm_begin_read
        self._begin_read.restype = ctypes.c_bool
        self._begin_write = pyrealm._realm_lib.realm_begin_write
        self._begin_write.restype = ctypes.c_bool
        self._commit = pyrealm._realm_lib.realm_commit
        self._commit.restype = ctypes.c_bool
        self._rollback = pyrealm._realm_lib.realm_rollback
        self._rollback.restype = ctypes.c_bool
        self._refresh = pyrealm._realm_lib.realm_refresh
        self._refresh.restype = ctypes.c_bool
        self._freeze = pyrealm._realm_lib.realm_freeze
        self._freeze.restype = ctypes.c_bool
        self._compact = pyrealm._realm_lib.realm_compact
        self._compact.restype = ctypes.c_bool
        self._get_schema_version = pyrealm._realm_lib.realm_get_schema_version
        self._get_schema_version.restype = ctypes.c_uint64
        self._get_num_classes = pyrealm._realm_lib.realm_get_num_classes
        self._get_num_classes.restype = ctypes.c_uint64
        self._get_schema = pyrealm._realm_lib.realm_get_schema
        self._get_schema.restype = ctypes.c_void_p
        self._get_class_keys = pyrealm._realm_lib.realm_get_class_keys
        self._get_class_keys.argtypes = [
            ctypes.POINTER(Realm._RealmObject),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t)
        ]
        self._get_class_keys.restype = ctypes.c_bool
        self._get_class = pyrealm._realm_lib.realm_get_class
        self._get_class.argtypes = [
            ctypes.POINTER(Realm._RealmObject),
            ctypes.c_uint32,
            ctypes.POINTER(RealmClassInfo)
        ]
        self._get_class.restype = ctypes.c_bool
        self._get_class_properties = pyrealm._realm_lib.realm_get_class_properties
        self._get_class_properties.argtypes = [
            ctypes.POINTER(Realm._RealmObject),
            ctypes.c_uint32,
            ctypes.POINTER(RealmPropertyInfo),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t)
        ]
        self._get_class_properties.restype = ctypes.c_bool


    @classmethod
    def get_version(cls):
        major = ctypes.c_int()
        minor = ctypes.c_int()
        patch = ctypes.c_int()
        extra = ctypes.c_char_p()
        pyrealm._realm_lib.realm_get_library_version.restype = ctypes.c_char_p
        version_stg = pyrealm._realm_lib.realm_get_library_version()
        result = pyrealm._realm_lib.realm_get_library_version_numbers(
            ctypes.byref(major), ctypes.byref(minor), ctypes.byref(patch), ctypes.byref(extra)
        )
        if not version_stg:
            version_stg = b''
        if result:
            return RealmVersion(version_stg.decode("ASCII"), major.value, minor.value, patch.value, extra.value.decode("ASCII"))
        else:
            return RealmVersion(version_stg.decode("ASCII"), 0, 0, 0, "")

    @property
    def config(self) -> RealmConfig:
        return self._config

    @property
    def closed(self) -> bool:
        return self._is_closed(self._realm)

    @property
    def writable(self) -> bool:
        return self._is_writable(self._realm)

    @property
    def num_versions(self) -> int:
        result = ctypes.c_ulonglong(0)
        if self._get_num_versions(self._realm, ctypes.byref(result)):
            return result.value
        else:
            throw_last_error("Error requesting number versions in Realm object")

    @property
    def transaction_version(self) -> Tuple[int, int]:
        found = ctypes.c_bool()
        result = Realm._RealmVersionId()
        if self._get_version_id(self._realm, ctypes.byref(found), ctypes.byref(result)):
            if found:
                return (result.version, result.index)
            else:
                return None
        else:
            throw_last_error("Error requesting current transaction version for Realm object")

    @property
    def schema_version(self) -> int:
        return self._get_schema_version(self._realm)

    @property
    def num_classes(self) -> int:
        return self._get_num_classes(self._realm)

    def get_class_keys(self) -> List[int]:
        out_num = ctypes.c_size_t()
        num = self.num_classes
        class_keys = (ctypes.c_uint32 * num)()
        if self._get_class_keys(self._realm, class_keys, num, ctypes.byref(out_num)):
            retval = [int(x) for x in class_keys]
            return retval
        else:
            throw_last_error("Error requesting class keys for Realm object")

    def get_class(self, class_key: int) -> RealmClassInfo:
        class_info = RealmClassInfo()
        if self._get_class(self._realm, ctypes.c_uint32(class_key), ctypes.byref(class_info)):
            return class_info
        else:
            throw_last_error("Error requesting class for Realm object")

    def get_class_properties(self, class_key: int, num_properties: int) -> List[RealmPropertyInfo]:
        out_num = ctypes.c_size_t()
        properties = (RealmPropertyInfo * num_properties)()
        if self._get_class_properties(self._realm, ctypes.c_uint32(class_key), properties, num_properties, ctypes.byref(out_num)):
            return list(properties)
        else:
            throw_last_error("Error requesting class for Realm object")

    def __str__(self):
        desc_str = (
            f"Realm: '{os.path.basename(self.config.path)}'"
            f"{'(encrypted)' if self.config.encryption_key else ''}"
        )
        if self.closed:
            desc_str += "- closed"
        else:
            desc_str += f" - num classes: {self.num_classes}"
        return desc_str

    def __repr__(self):
        return f"<{str(self)}>"

    def info(self, prepend: str = "") -> str:
        states = []
        states.append('Closed') if self.closed else states.append('Open')
        states.append('Writable') if self.writable else None
        states.append('Encrypted') if self.config.encryption_key else None
        return (
            f"{prepend}Realm Information\n"
            f"{prepend}- Path: {self.config.path}\n"
            f"{prepend}- State: {', '.join(states)}\n"
            f"{prepend}- Schema version: {self.schema_version} (num: {self.num_versions})\n"
            f"{prepend}- Current transaction: {self._transaction.name}\n"
            f"{prepend}- Transaction version ID: {self.transaction_version}\n"
            f"{prepend}- Number of classes: {self.num_classes} {self.get_class_keys()}\n"
        )

    def delete_files(self) -> bool:
        result = ctypes.c_bool
        if self._delete_files(self._realm, ctypes.byref(result)):
            return result
        else:
            throw_last_error("Error deleting files for Realm object")

    def close(self) -> bool:
        if not self._close(self._realm):
            throw_last_error("Error closing Realm object")
        return True

    def begin_read(self):
        with self._lock:
            if self._transaction == Realm._Transaction.NONE:
                if self._begin_read(self._realm):
                    self._transaction = Realm._Transaction.READ
                    return True
                else:
                    throw_last_error("Error beginning read transaction")
            else:
                raise RealmException("Another transaction is already in progress")

    def begin_write(self) -> bool:
        with self._lock:
            if self._transaction == Realm._Transaction.NONE:
                if self._begin_write(self._realm):
                    self._transaction = Realm._Transaction.WRITE
                    return True
                else:
                    throw_last_error("Error beginning write transaction")
            else:
                raise RealmException("Another transaction is already in progress")

    def commit(self) -> bool:
        with self._lock:
            if self._transaction != Realm._TransactionType.NONE:
                if self._commit(self._realm):
                    self._transaction = Realm._TransactionType.NONE
                    return True
                else:
                    throw_last_error("Error committing current transaction")
            else:
                return False

    def rollback(self) -> bool:
        with self._lock:
            if self._transaction != Realm._TransactionType.NONE:
                if self._rollback(self._realm):
                    self._transaction = Realm._TransactionType.NONE
                    return True
                else:
                    throw_last_error("Error rolling back current transaction")
            else:
                return False

    def refresh(self) -> bool:
        result = ctypes.c_bool
        if self._refresh(self._realm, ctypes.byref(result)):
            return result
        else:
            throw_last_error("Error refreshing Realm object")

    def freeze(self) -> bool:
        result = ctypes.c_bool
        if self._freeze(self._realm, ctypes.byref(result)):
            return result
        else:
            throw_last_error("Error refreshing Realm object")

    def compact(self) -> bool:
        result = ctypes.c_bool
        if self._compact(self._realm, ctypes.byref(result)):
            return result
        else:
            throw_last_error("Error compacting Realm object")

    def write(self) -> 'TransactionContextHandler':
        return TransactionContextHandler(self, Realm._TransactionType.WRITE)

    def read(self) -> 'TransactionContextHandler':
        return TransactionContextHandler(self, Realm._TransactionType.READ)


class TransactionContextHandler():
    # Class to handle the transaction when used in a context (e.g. `with realm.read() as t:`)
    def __init__(self, realm: Realm, xact_type: Realm._TransactionType):
        if realm is None:
            raise ValueError("Realm cannot be none")
        if xact_type is Realm._TransactionType.NONE:
            raise ValueError("Transaction type cannot be NONE")

        self._realm = realm
        self._xact_type = xact_type

    def __enter__(self):
        if self._xact_type == Realm._TransactionType.READ:
            self._realm.begin_read()
        elif self._xact_type == Realm._TransactionType.WRITE:
            self._realm.begin_write()
        else:
            raise ValueError(f"Transaction type is invalid: {self._xact_type}")
        return self

    def __exit__(self, _exc_type, exc_value, _trace):
        # If the transaction hasn't been cancelled and an exception was not thrown, then commit it
        if exc_value is None and self._transaction != Realm._TransactionType.NONE:
            # If the transaction has already been committed or cancelled directly on the realm object,
            # this will do nothing
            self._realm.commit()
        # Exception was thrown, roll back the transaction
        else:
            self.cancel()

    def cancel(self):
        # Canceling the transaction before the contect has been completed
        if self._xact_type != Realm._TransactionType.NONE:
            self._xact_type = Realm._TransactionType.NONE
            # If the transaction has already been committed or cancelled directly on the realm object,
            # this will do nothing
            self._realm.rollback()
