import ctypes

from enum import IntEnum
from typing import List

import pyrealm
from .schema import RealmObject


class RealmSchemaMode(IntEnum):
    RLM_SCHEMA_MODE_AUTOMATIC = 0
    RLM_SCHEMA_MODE_IMMUTABLE = 1
    RLM_SCHEMA_MODE_READ_ONLY = 2
    RLM_SCHEMA_MODE_SOFT_RESET_FILE = 3
    RLM_SCHEMA_MODE_HARD_RESET_FILE = 4
    RLM_SCHEMA_MODE_ADDITIVE_DISCOVERED = 5
    RLM_SCHEMA_MODE_ADDITIVE_EXPLICIT = 6
    RLM_SCHEMA_MODE_MANUAL = 7


class RealmConfig():

    class _ConfigObject(ctypes.Structure):
        pass

    def __init__(
        self,
        path: str = None,
        read_only: bool = True,
        in_memory: bool = False,
        schema_version: int = 0,
        schema: List[RealmObject] = None,
    ):
        self._init_if()
        self._config = self._new_config()

        if path:
            self.path = path
        self.in_memory = in_memory
        if read_only:
            self.schema_mode =  RealmSchemaMode.RLM_SCHEMA_MODE_READ_ONLY
        else:
            self.schema_mode = RealmSchemaMode.RLM_SCHEMA_MODE_AUTOMATIC
        self.schema_version = schema_version

    def _init_if(self) -> None:
        # Set up the interface for the Realm config functions
        self._new_config = pyrealm._realm_lib.realm_config_new
        self._new_config.restype = ctypes.POINTER(RealmConfig._ConfigObject)
        self._set_path = pyrealm._realm_lib.realm_config_set_path
        self._get_path = pyrealm._realm_lib.realm_config_get_path
        self._get_path.restype = ctypes.c_char_p
        self._get_encryption_key = pyrealm._realm_lib.realm_config_get_encryption_key
        self._get_encryption_key.restype = ctypes.c_ulong
        self._set_encryption_key = pyrealm._realm_lib.realm_config_set_encryption_key
        self._get_schema_version = pyrealm._realm_lib.realm_config_get_schema_version
        self._get_schema_version.restype = ctypes.c_uint64
        self._set_schema_version = pyrealm._realm_lib.realm_config_set_schema_version
        self._get_schema_mode = pyrealm._realm_lib.realm_config_get_schema_mode
        self._get_schema_mode.restype = ctypes.c_uint64
        self._set_schema_mode = pyrealm._realm_lib.realm_config_set_schema_mode
        self._get_disable_format_upgrade = pyrealm._realm_lib.realm_config_get_disable_format_upgrade
        self._get_disable_format_upgrade = ctypes.c_bool
        self._set_disable_format_upgrade = pyrealm._realm_lib.realm_config_set_disable_format_upgrade
        self._get_force_sync_history = pyrealm._realm_lib.realm_config_get_force_sync_history
        self._get_force_sync_history.restype = ctypes.c_bool
        self._set_force_sync_history = pyrealm._realm_lib.realm_config_set_force_sync_history
        self._get_automatic_change_notifications = pyrealm._realm_lib.realm_config_get_automatic_change_notifications
        self._get_automatic_change_notifications.restype = ctypes.c_bool
        self._set_automatic_change_notifications = pyrealm._realm_lib.realm_config_set_automatic_change_notifications
        self._get_max_number_of_active_versions = pyrealm._realm_lib.realm_config_get_max_number_of_active_versions
        self._get_max_number_of_active_versions.restype = ctypes.c_uint64
        self._set_max_number_of_active_versions = pyrealm._realm_lib.realm_config_set_max_number_of_active_versions
        self._get_in_memory = pyrealm._realm_lib.realm_config_get_in_memory
        self._get_in_memory.restype = ctypes.c_bool
        self._set_in_memory = pyrealm._realm_lib.realm_config_set_in_memory
        self._get_fifo_path = pyrealm._realm_lib.realm_config_get_fifo_path
        self._get_fifo_path.restype = ctypes.c_char_p
        self._set_fifo_path = pyrealm._realm_lib.realm_config_set_fifo_path
        self._get_cached = pyrealm._realm_lib.realm_config_get_cached
        self._get_cached.restype = ctypes.c_bool
        self._set_cached = pyrealm._realm_lib.realm_config_set_cached

    @property
    def path(self) -> str:
        value = self._get_path(self._config)
        if value:
            return value.decode('ASCII')
        else:
            return ""

    @path.setter
    def path(self, path: str):
        if path:
            self._set_path(self._config, ctypes.c_char_p(path.encode('utf-8')))
        else:
            raise ValueError("Path cannot be empty")

    @property
    def encryption_key(self) -> bytes:
        buf = ctypes.create_string_buffer(100)
        keylen = self._get_encryption_key(self._config, buf)
        if keylen > 0:
            return buf.raw[:keylen]
        else:
            return b''

    @encryption_key.setter
    def encryption_key(self, key: bytes) -> bool:
        if key is None:
            key = b''
        elif len(key) not in [0, 64]:
            raise ValueError(f"Encryption key length must be 0 or 64 - got {len(key)} bytes")
        return self._set_encryption_key(self._config, ctypes.c_char_p(key), ctypes.c_int(len(key)))

    @property
    def schema_version(self) -> int:
        return self._get_schema_version(self._config)

    @schema_version.setter
    def schema_version(self, num: int):
        self._set_schema_version(self._config, ctypes.c_uint64(num))

    @property
    def schema_mode(self) -> RealmSchemaMode:
        result = self._get_schema_mode(self._config)
        return RealmSchemaMode(result)

    @schema_mode.setter
    def schema_mode(self, mode: RealmSchemaMode):
        if not isinstance(mode, RealmSchemaMode):
            raise TypeError(f"Invalid schema mode type: {type(mode)}")
        self._set_schema_mode(self._config, ctypes.c_int(mode.value))

    @property
    def disable_format_upgrade(self) -> bool:
        return self._get_disable_format_upgrade(self._config)

    @disable_format_upgrade.setter
    def disable_format_upgrade(self, disable: bool):
        self._set_disable_format_upgrade(self._config, ctypes.c_bool(disable))

    @property
    def force_sync_history(self) -> bool:
        return self._get_force_sync_history(self._config)

    @force_sync_history.setter
    def force_sync_history(self, force: bool):
        self._set_force_sync_history(self._config, ctypes.c_bool(force))

    @property
    def automatic_change_notifications(self) -> bool:
        return self._get_automatic_change_notifications(self._config)

    @automatic_change_notifications.setter
    def automatic_change_notifications(self, force: bool):
        self._set_automatic_change_notifications(self._config, ctypes.c_bool(force))

    @property
    def force_sync_history(self) -> bool:
        return self._get_force_sync_history(self._config)

    @force_sync_history.setter
    def force_sync_history(self, force: bool):
        self._set_force_sync_history(self._config, ctypes.c_bool(force))

    @property
    def max_number_of_active_versions(self) -> int:
        return self._get_max_number_of_active_versions(self._config)

    @max_number_of_active_versions.setter
    def max_number_of_active_versions(self, num: int):
        self._set_max_number_of_active_versions(self._config, ctypes.c_uint64(num))

    @property
    def in_memory(self) -> bool:
        return self._get_in_memory(self._config)

    @in_memory.setter
    def in_memory(self, enable: bool):
        self._set_in_memory(self._config, ctypes.c_bool(enable))

    @property
    def fifo_path(self) -> str:
        result = self._get_fifo_path(self._config)
        if result:
            return result.decode("ASCII")
        else:
            return ""

    @fifo_path.setter
    def fifo_path(self, path: str):
        if path is not None:
            self._set_fifo_path(self._config, ctypes.c_char_p(path.encode('utf-8')))
        else:
            raise ValueError("Fifo path cannot be none")

    @property
    def cached(self) -> bool:
        return self._get_cached(self._config)

    @cached.setter
    def cached(self, enable: bool):
        self._set_cached(self._config, ctypes.c_bool(enable))

    def __str__(self):
        return f"RealmConfig: '{self.path}'{', encrypted' if self.encryption_key else ''}"

    def __repr__(self):
        return f"<{str(self)}>"

    def info(self, prepend: str = "") -> str:
        return (
            f"{prepend}Realm Config Information\n"
            f"{prepend}- Realm path:               {self.path}\n"
            f"{prepend}- Realm key:                {self.encryption_key}\n"
            f"{prepend}- Realm schema version:     {self.schema_version}\n"
            f"{prepend}- Realm schema mode:        {self.schema_mode.name}\n"
            f"{prepend}- Realm format upgrade:     {not self.disable_format_upgrade}\n"
            f"{prepend}- Realm change notif:       {self.automatic_change_notifications}\n"
            f"{prepend}- Realm force sync:         {self.force_sync_history}\n"
            f"{prepend}- Realm max versions:       {self.max_number_of_active_versions}\n"
            f"{prepend}- Realm in memory:          {self.in_memory}\n"
            f"{prepend}- Realm fifo path:          {self.fifo_path}\n"
            f"{prepend}- Realm cached:             {self.cached}"
        )



