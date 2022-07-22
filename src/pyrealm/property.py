import ctypes

from abc import ABC
from collections import OrderedDict
from enum import (IntEnum, IntFlag)
from typing import (Any, Dict, List, Type, Union)

class RealmPropertyFlags(IntFlag):
    RLM_PROPERTY_NORMAL = 0
    RLM_PROPERTY_NULLABLE = 1
    RLM_PROPERTY_PRIMARY_KEY = 2
    RLM_PROPERTY_INDEXED = 4


class RealmPropertyType(IntEnum):
    RLM_PROPERTY_TYPE_INT = 0
    RLM_PROPERTY_TYPE_BOOL = 1
    RLM_PROPERTY_TYPE_STRING = 2
    RLM_PROPERTY_TYPE_BINARY = 4
    RLM_PROPERTY_TYPE_MIXED = 6
    RLM_PROPERTY_TYPE_TIMESTAMP = 8
    RLM_PROPERTY_TYPE_FLOAT = 9
    RLM_PROPERTY_TYPE_DOUBLE = 10
    RLM_PROPERTY_TYPE_DECIMAL128 = 11
    RLM_PROPERTY_TYPE_OBJECT = 12
    RLM_PROPERTY_TYPE_LINKING_OBJECTS = 14
    RLM_PROPERTY_TYPE_OBJECT_ID = 15
    RLM_PROPERTY_TYPE_UUID = 17


class RealmCollectionType(IntEnum):
    RLM_COLLECTION_TYPE_NONE = 0
    RLM_COLLECTION_TYPE_LIST = 1
    RLM_COLLECTION_TYPE_SET = 2
    RLM_COLLECTION_TYPE_DICTIONARY = 4


class RealmPropertyInfo(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("public_name", ctypes.c_char_p),
        ("type", ctypes.c_int),
        ("collection_type", ctypes.c_int),
        ("link_target", ctypes.c_char_p),
        ("link_origin_property_name", ctypes.c_char_p),
        ("key", ctypes.c_int64),
        ("flags", ctypes.c_int),
    ]


class PropertyValue():
    def __init__(self, prop: 'PropertyType', value: Any = None):
        if not issubclass(type(prop), PropertyType):
            raise TypeError("Property value can only be created with a property type")
        self._value = None
        self._property = prop
        if value is not None:
            self.value

    @property
    def name(self):
        return self._property.name

    @property
    def rtype(self):
        return self._property.rtype

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: Any):
        if value is None and not self.is_nullable:
            raise ValueError(f"Property '{self.name}' is not nullable")
        else:
            self._value = PropertyType.convert_value(self.rtype, value)

    @property
    def is_nullable(self):
        return self._property.is_nullable

    def __str__(self):
        return f"<{self._property.__class__.__name__}: '{self.name}' = {self.value}>"

    def __repr__(self):
        return str(self)


class PropertyType(ABC):
    def __init__(
        self,
        name: str = "",
        public_name: str = "",
        rtype: RealmPropertyType = None,
        link_class: str = "",
        link_property: str = ""
    ):
        self._name = name
        self._public_name = public_name
        self._type = rtype
        self._collection_type = RealmCollectionType.RLM_COLLECTION_TYPE_NONE
        self._link_target = link_class
        self._link_origin_property_name = link_property
        self._key = 0
        self._flags = 0
        self._value = 0

    def new(self, value: Any = None):
        return PropertyValue(self, value)

    @property
    def name(self):
        return self._name

    @property
    def public_name(self):
        return self._public_name

    @property
    def rtype(self):
        return self._type

    @property
    def flags(self):
        return self._flags

    @property
    def is_nullable(self):
        return self._flags & RealmPropertyFlags.RLM_PROPERTY_NULLABLE

    @property
    def is_primary_key(self):
        return self._flags & RealmPropertyFlags.RLM_PROPERTY_PRIMARY_KEY

    @property
    def collection_type(self):
        return self._collection_type

    def _set_name(self, new_name: str):
        self._name = new_name

    def describe(self):
        type_stg = f"{self.__class__.__name__}{'?' if self.is_nullable else ''}"
        if self._collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_LIST:
            type_stg = f"List<{type_stg}>"
        elif self._collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_SET:
            type_stg = f"Set<{type_stg}>"
        elif self._collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_DICTIONARY:
            type_stg = f"Dictionary<{type_stg}>"
        return f"{type_stg}{'(primary key)' if self.is_primary_key else ''}"

    def __str__(self):
        return f"<{self.describe()}: '{self.name}'>"

    def __repr__(self):
        return str(self)

    def get_property_info(self):
        prop_info = RealmPropertyInfo()
        prop_info.name = self.name
        prop_info.public_name = self.public_name
        prop_info.type = self.rtype.value
        prop_info.collection_type = self.collection_type.value
        prop_info.link_target = self._link_target
        prop_info.link_origin_property_name = self._link_origin_property_name
        prop_info.key = self._key
        prop_info.flags = self._flags.value
        return prop_info

    @classmethod
    def new_from_property_info(cls, prop_info: RealmPropertyInfo):
        prop_class = cls._get_property_class(prop_info.type)
        prop_obj = None
        if prop_class is None:
            raise ValueError(f"Property type {prop_info.type} is unknown or not supported")
        if prop_info.type == RealmPropertyType.RLM_PROPERTY_TYPE_LINKING_OBJECTS:
            prop_obj = prop_class(
                link_class=prop_info.link_target,
                link_property=prop_info.link_origin_property_name,
                public_name=prop_info.public_name)
        else:
            prop_obj = prop_class(public_name=prop_info.public_name)
        prop_obj.set_name(prop_info.name)
        prop_obj._key = prop_info.key
        prop_obj._flags = RealmPropertyFlags(prop_info.flags)
        prop_obj._collection_type = RealmCollectionType(prop_info.collection_type)
        if (prop_obj._flags & RealmPropertyFlags.RLM_PROPERTY_NULLABLE):
            prop_obj = Nullable(prop_obj)
        prop_obj = cls._wrap_collection_type(prop_obj)
        if (prop_obj._flags & RealmPropertyFlags.RLM_PROPERTY_PRIMARY_KEY):
            prop_obj = PrimaryKey(prop_obj)

        return prop_obj

    @classmethod
    def _get_property_class(cls, rtype: RealmPropertyType) -> Type['PropertyType']:
        if rtype == RealmPropertyType.RLM_PROPERTY_TYPE_INT:
            return RealmInt
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_BOOL:
            return RealmBool
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_STRING:
            return RealmString
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_BINARY:
            return RealmBinary
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_MIXED:
            return RealmMixed
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_TIMESTAMP:
            return RealmTimestamp
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_FLOAT:
            return RealmFloat
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_DOUBLE:
            return RealmDouble
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_DECIMAL128:
            return RealmDecimal128
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT:
            return RealmObject
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_LINKING_OBJECTS:
            return RealmLinkingObject
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT_ID:
            return RealmObjectID
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_UUID:
            return RealmUUID
        else:
            raise ValueError(f"Property type '{rtype}' is invalid")

    @classmethod
    def _wrap_collection_type(cls, prop: 'PropertyType') -> 'PropertyType':
        if prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_NONE:
            return prop
        elif prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_LIST:
            return RealmList(prop)
        elif prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_SET:
            return RealmSet(prop)
        elif prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_DICTIONARY:
            return RealmDictionary(prop)
        else:
            raise ValueError(f"Property collection type '{prop.collection_type}' is invalid")

    @classmethod
    def convert_value(cls, rtype: RealmPropertyType, value: Any):
        raise_type_error = False
        if rtype == RealmPropertyType.RLM_PROPERTY_TYPE_INT:
            return cls._convert_int_value(value)
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_BOOL:
            return cls._convert_bool_value(value)
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_STRING:
            return cls._convert_string_value(value)
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_BINARY:
            return cls._convert_binary_value(value)
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_FLOAT or \
            rtype == RealmPropertyType.RLM_PROPERTY_TYPE_DOUBLE:
            return cls._convert_float_value(value)
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_MIXED:
            return value
        else:
            raise TypeError(f"Property type {rtype.name} is not supported")

    @classmethod
    def _convert_int_value(cls, value: Any):
        if isinstance(value, int):
            return value
        else:
            raise TypeError(f"expected int but got {type(value)}")

    @classmethod
    def _convert_bool_value(cls, value: Any):
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ['true', 't', 'yes', 'y']
        elif isinstance(value, int):
            return value != 0
        else:
            raise TypeError(f"expected bool but got {type(value)}")

    @classmethod
    def _convert_str_value(cls, value: Any):
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode("ASCII")
        else:
            raise TypeError(f"expected str but got {type(value)}")

    @classmethod
    def _convert_binary_value(cls, value: Any):
        if isinstance(value, bytes):
            return value
        else:
            raise TypeError(f"expected bytes but got {type(value)}")

    @classmethod
    def _convert_float_value(cls, value: Any):
        if isinstance(value, float):
            return value
        elif isinstance(value, int):
            return float(value)
        else:
            raise TypeError(f"expected bytes but got {type(value)}")


class PropertyWrapper(ABC):
    def __init__(self, prop: Union[PropertyType, 'PropertyWrapper']):
        if prop is None:
            ValueError("prop value cannot be None")
        elif issubclass(type(prop), PropertyType):
            self._property = prop
        elif issubclass(type(prop), PropertyWrapper):
            self._property = prop._property
        else:
            TypeError(f"Expected property type or wrapper, got {prop}")

    # Wrappted methods call the property equivalents
    def new(self, value: Any = None):
        return self._property.new(value)

    @property
    def name(self):
        return self._property.name

    @property
    def public_name(self):
        return self._property.public_name

    @property
    def rtype(self):
        return self._property.rtype

    @property
    def flags(self):
        return self._property.flags

    @property
    def is_nullable(self):
        return self._property.is_nullable

    @property
    def is_primary_key(self):
        return self._property.is_primary_key

    def _set_name(self, new_name: str):
        self._property.set_name(new_name)

    def describe(self):
        return self._property.describe()

    def __str__(self):
        return str(self._property)

    def __repr__(self):
        return repr(self._property)


class Nullable(PropertyWrapper):
    def __init__(self, prop: Union[PropertyType, 'PropertyWrapper']):
        super().__init__(prop)
        self._property._flags |= RealmPropertyFlags.RLM_PROPERTY_NULLABLE


class PrimaryKey(PropertyWrapper):
    def __init__(self, prop: Union[PropertyType, 'PropertyWrapper']):
        super().__init__(prop)
        self._property._flags |= RealmPropertyFlags.RLM_PROPERTY_PRIMARY_KEY


class RealmSet(PropertyWrapper):
    def __init__(self, prop: Union[PropertyType, 'PropertyWrapper']):
        super().__init__(prop)
        if self._property._collection_type != RealmCollectionType.RLM_COLLECTION_TYPE_NONE:
            raise ValueError("Property collection types cannot be combined")
        else:
            self._property._collection_type = RealmCollectionType.RLM_COLLECTION_TYPE_SET


class RealmList(PropertyWrapper):
    def __init__(self, prop: Union[PropertyType, 'PropertyWrapper']):
        super().__init__(prop)
        if self._property._collection_type != RealmCollectionType.RLM_COLLECTION_TYPE_NONE:
            raise ValueError("Property collection types cannot be combined")
        else:
            self._property._collection_type = RealmCollectionType.RLM_COLLECTION_TYPE_LIST


class RealmDictionary(PropertyWrapper):
    def __init__(self, prop: Union[PropertyType, 'PropertyWrapper']):
        super().__init__(prop)
        if self._collection_type != RealmCollectionType.RLM_COLLECTION_TYPE_NONE:
            raise ValueError("Property collection types cannot be combined")
        else:
            self._collection_type = RealmCollectionType.RLM_COLLECTION_TYPE_DICTIONARY


class RealmInt(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_INT)


class RealmBool(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_BOOL)


class RealmString(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_STRING)


class RealmBinary(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_BINARY)


class RealmMixed(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_MIXED)


class RealmTimestamp(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_TIMESTAMP)


class RealmFloat(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_FLOAT)


class RealmDouble(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_DOUBLE)


class RealmDecimal128(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_DECIMAL128)


class RealmObject(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT)


class RealmLinkingObject(PropertyType):
    def __init__(self, link_class: str, link_property: str, public_name: str = ""):
        # name will be set later
        super().__init__(
            public_name=public_name,
            rtype=RealmPropertyType.RLM_PROPERTY_TYPE_LINKING_OBJECTS,
            link_class=link_class,
            link_property=link_property
        )


class RealmObjectID(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT_ID)


class RealmUUID(PropertyType):
    def __init__(self, public_name: str = ""):
        # name will be set later
        super().__init__(public_name=public_name, rtype=RealmPropertyType.RLM_PROPERTY_TYPE_UUID)
