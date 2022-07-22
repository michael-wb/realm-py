import ctypes

from enum import IntEnum
from typing import Optional

import pyrealm


class RealmErrorNo(IntEnum):
    RLM_ERR_NONE = 0
    RLM_ERR_UNKNOWN = 1
    RLM_ERR_OTHER_EXCEPTION = 2
    RLM_ERR_OUT_OF_MEMORY = 3
    RLM_ERR_NOT_CLONABLE = 4

    RLM_ERR_NOT_IN_A_TRANSACTION = 5
    RLM_ERR_WRONG_THREAD = 6

    RLM_ERR_INVALIDATED_OBJECT = 7
    RLM_ERR_INVALID_PROPERTY = 8
    RLM_ERR_MISSING_PROPERTY_VALUE = 9
    RLM_ERR_PROPERTY_TYPE_MISMATCH = 10
    RLM_ERR_MISSING_PRIMARY_KEY = 11
    RLM_ERR_UNEXPECTED_PRIMARY_KEY = 12
    RLM_ERR_WRONG_PRIMARY_KEY_TYPE = 13
    RLM_ERR_MODIFY_PRIMARY_KEY = 14
    RLM_ERR_READ_ONLY_PROPERTY = 15
    RLM_ERR_PROPERTY_NOT_NULLABLE = 16
    RLM_ERR_INVALID_ARGUMENT = 17

    RLM_ERR_LOGIC = 18
    RLM_ERR_NO_SUCH_TABLE = 19
    RLM_ERR_NO_SUCH_OBJECT = 20
    RLM_ERR_CROSS_TABLE_LINK_TARGET = 21
    RLM_ERR_UNSUPPORTED_FILE_FORMAT_VERSION = 22
    RLM_ERR_MULTIPLE_SYNC_AGENTS = 23
    RLM_ERR_ADDRESS_SPACE_EXHAUSTED = 24
    RLM_ERR_MAXIMUM_FILE_SIZE_EXCEEDED = 25
    RLM_ERR_OUT_OF_DISK_SPACE = 26
    RLM_ERR_KEY_NOT_FOUND = 27
    RLM_ERR_COLUMN_NOT_FOUND = 28
    RLM_ERR_COLUMN_ALREADY_EXISTS = 29
    RLM_ERR_KEY_ALREADY_USED = 30
    RLM_ERR_SERIALIZATION_ERROR = 31
    RLM_ERR_INVALID_PATH_ERROR = 32
    RLM_ERR_DUPLICATE_PRIMARY_KEY_VALUE = 33

    RLM_ERR_INDEX_OUT_OF_BOUNDS = 34

    RLM_ERR_INVALID_QUERY_STRING = 35
    RLM_ERR_INVALID_QUERY = 36

    RLM_ERR_FILE_ACCESS_ERROR = 37
    RLM_ERR_FILE_PERMISSION_DENIED = 38

    RLM_ERR_DELETE_OPENED_REALM = 39
    RLM_ERR_ILLEGAL_OPERATION = 40

    RLM_ERR_CALLBACK = 1000000  # A user-provided callback failed


class RealmLogicError(IntEnum):
    RLM_LOGIC_ERR_NONE = 0
    RLM_LOGIC_ERR_STRING_TOO_BIG = 1


class RealmError(ctypes.Structure):
    class _Kind(ctypes.Union):
        _fields_ = [
            ("code", ctypes.c_int),
            ("logic_error_kind", ctypes.c_int),
        ]

RealmError._fields_ = [
    ("error", ctypes.c_int),
    ("message", ctypes.c_char_p),
    ("usercode_error", ctypes.c_void_p),
    ("kind", RealmError._Kind),
]

class RealmException(Exception):

    def __init__(self, realm_err: Optional[RealmError] = None, message: Optional[str] = None):
        self.errorno = RealmErrorNo.RLM_ERR_NONE
        self.errmessage = message
        self.kind = RealmLogicError.RLM_LOGIC_ERR_NONE
        self.code = 0

        if realm_err:
            self.errorno = RealmErrorNo(realm_err.error.value)
            errmsg = realm_err.message.decode("ASCII") if realm_err.messsage else message if message is not None else ""
            self.errmessage = f"{self.errorno.name}: {errmsg}"
            if self.errorno == RealmErrorNo.RLM_ERR_LOGIC:
                self.kind = RealmLogicError(realm_err.kind.logic_error_kind.value)
            else:
                self.code = RealmLogicError(realm_err.kind.code.value)

        super().__init__(self.errmessage)

    def __str__(self):
        return self.errmessage

    def __repr__(self):
        return f"<RealmException:{self.errmessage}>"


def get_last_error(clear_error: bool = False) -> RealmException:
    pyrealm.realm_lib.realm_get_last_error.restype = ctypes.c_bool
    realm_err = RealmError()
    realm_ex = None
    if pyrealm.realm_lib.realm_get_last_error(ctypes.byref(realm_err)):
        if realm_err:
            realm_ex = RealmException(realm_err=realm_err)
    if clear_error:
        clear_last_error()
    return realm_ex

def throw_last_error(alt_message: str = "", clear_error: bool = True):
    realm_ex = get_last_error(clear_error)
    if realm_ex:
        raise realm_ex
    elif alt_message:
        raise RealmException(message=alt_message)

def clear_last_error() -> bool:
    pyrealm.realm_lib.realm_clear_last_error.restype = ctypes.c_bool
    return pyrealm.realm_lib.realm_clear_last_error()
