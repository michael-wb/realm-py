from ast import Str
import ctypes

from collections import OrderedDict
from enum import IntFlag
from typing import (Any, Dict, List,)

from .property import PropertyType

class RealmClassFlags(IntFlag):
    RLM_CLASS_NORMAL = 0
    RLM_CLASS_EMBEDDED = 1
    RLM_CLASS_ASYMMETRIC = 2
    RLM_CLASS_MASK = 3


class RealmClassInfo(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("primary_key", ctypes.c_char_p),
        ("num_properties", ctypes.c_ulong),
        ("num_computed_properties", ctypes.c_ulong),
        ("key", ctypes.c_uint32),
        ("flags", ctypes.c_int),
    ]


class RealmObjectMeta(type):
    def __new__(cls, clsname, bases, attrs):
        # Don't process the schema object base class
        if clsname == "RealmObject":
            return super(RealmObjectMeta, cls).__new__(cls, clsname, bases, attrs)

        new_class = super(RealmObjectMeta, cls).__new__(cls, clsname, bases, attrs)
        setattr(new_class, '__name', clsname)
        setattr(new_class, '__flags', RealmClassFlags.RLM_CLASS_NORMAL)
        setattr(new_class, '__properties', OrderedDict())

        # Move the class properties into the _properties list
        for x in attrs:
            x_obj = getattr(new_class, x, None)
            if x_obj is not None and PropertyType in x_obj.__class__.__bases__:
                x_obj._set_name(x)
                new_class._properties[x_obj.name] = x_obj
                delattr(new_class, x)

        return new_class


class RealmObject(metaclass=RealmObjectMeta):
    def __init__(self, *args: List[Any], **kwargs: Dict[str, Any]):
        # double underscores so it skips the __[get|set]attr__ checking
        # This also allows property names that start with an underscore
        self.__property_values = OrderedDict()
        if (len(args) + len(kwargs)) == 0:
            for x in self._properties:
                x_val = x.new()
                self.__property_values[x_val.name] = x_val
        else:
            props = self.property_names
            # Set the args values
            for i in range(len(args)):
                x = props.pop(0)
                self.__property_values[x] = self.__properties[x].new(args[i])

            while props:
                x = props.pop(0)
                if x in kwargs:
                    self.__property_values[x] = self.__properties[x].new(kwargs[x])
                elif self.__properties[x].is_nullable:
                    self.__property_values[x] = self.__properties[x].new(None)
                else:
                    raise ValueError("Property '{name}' was not intialized and is not nullable")

    @property
    def name(self):
        return self.__name

    @property
    def flags(self):
        return self.__flags

    @property
    def num_properties(self):
        return len(self.__properties)

    @property
    def property_names(self):
        return list(self.__properties)


    def __getattr__(self, name):
        if not name.startswith('__') and name in self.__property_values:
            return self.__property_values[name].value
        else:
            return super().__getattr__(name)


    def __setattr__(self, name, value):
        if not name.startswith('__') and name in self.__property_values:
            self.__property_values[name].value = value
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        if not name.startswith('__') and name in self.__property_values:
            raise RuntimeError('Cannot delete properties')
        elif name not in ["__name", "__flags", "__properties", "__property_values"]:
            super().__delattr__(name)
        else:
            raise AttributeError("Cannot delete property internal attributes")

    def __getitem__(self, key):
        if isinstance(key, int):
            if key >= 0 and key < self.num_properties:
                return self.__property_values[self.property_names[key]].value
        elif isinstance(key, str):
            if key in self.__property_values:
                return self.__property_values[key].value
            else:
                raise KeyError(f"Invalid property name: {key}")
        raise IndexError(f"Invalid property index value: {key}")

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if key >= 0 and key < self.num_properties:
                self.__property_values[self.property_names[key]].value = value
        elif isinstance(key, str):
            if key in self.__property_values:
                self.__property_values[key].value = value
            else:
                raise KeyError(f"Invalid property name: {key}")
        raise IndexError(f"Invalid property index value: {key}")

    def __delitem__(self, key, value):
        raise RuntimeError(f"Cannot delete properties")

    def describe(self):
        result= (f"Class: {self.name}\n"
                "--------------------------------------------------------")

