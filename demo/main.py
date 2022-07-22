import cmd
import os
import sys

from pathlib import Path
from typing import (
    Any,
    List,
)

from pyrealm import (
    realm_init,
    get_lib_path,
    num_realms,
    num_open_realms,
    close_realms,
    _opened_realms,
)

from pyrealm.config import RealmConfig
from pyrealm.realm import Realm
from pyrealm.property import (RealmCollectionType, RealmPropertyInfo, RealmPropertyFlags, RealmPropertyType)
from pyrealm.schema import (RealmClassInfo, RealmClassFlags)

#if __name__ == "__main__":
#
#    version = Realm.get_version()
#    print(f"Realm version: {str(version)}")
#
#    config = Config()
#    config.path = "./realm-demo/demo-v22.realm"
#    #config.encryption_key = b'1234567890123456789012345678901234567890123456789012345678901234'
#    print(config.info())
#
#    print("Opening new realm")
#    realm = Realm(config)
#    print(f"Realm closed:           {realm.closed}")
#    print(f"Realm writable:         {realm.writable}")
#    print(f"Realm num versions:     {realm.num_versions}")
#    print(f"Realm version id:       {realm.version_id}")
#    print(f"Realm schema version:   {realm.schema_version}")
#    print(f"Realm num classes:      {realm.num_classes}")
#    realm.close()
#    print("Realm closed")
#    print(f"Realm closed:           {realm.closed}")


class RealmDemoShell(cmd.Cmd):
    intro = 'Welcome to the Realm demo shell.   Type help or ? to list commands.\n'
    prompt = 'realm> '
    config = None
    realm = None

    def __init__(self):
        super().__init__()
        self.realms = []
        self.active_realm = None
        self.realm_name = ""

    # ----- basic turtle commands -----
    def do_info(self, arg):
        'Display information about the Realm Python Library'
        global _opened_realms
        print("Realm Python Library")
        print(f"- Realm version: {Realm.get_version()}")
        print(f"- Lib path: {get_lib_path()}")
        print(f"- All realms: {num_open_realms()} currently open")
        self.print_realms(_opened_realms, active=self.active_realm, prepend="  ")
        print()

    def do_realm(self, arg):
        """
        Select an opened realm or display the list of opened realms
           list     - print the list of opened realms (default)
           INDEX    - print information about the config provided to the realm
        """
        if not arg or arg == "list":
            print(f"Number of opened realms: {len(self.realms)}")
            self.print_realms(self.realms, active=self.active_realm)
            print()
        else:
            arg = check_int_value(arg, 1, len(self.realms))
            if arg != -1:
                self.active_realm = self.realms[arg-1]

    def do_open(self, arg):
        'Open a local, read-only realm at the specified path'
        if not arg:
            print("Please specify path for realm to open")
        else:
            self.open_realm(arg)

    def do_close(self, arg):
        """
        Close the active realm or realm at index from the 'realm' list
           INDEX    - optional index for the realm to close
        """
        realm = None
        if not self.realms:
            print("No realm has been opened")
        elif not arg:
            if self.active_realm:
                realm = self.active_realm
                self.active_realm = None
            else:
                print("No realm has been selected")
        else:
            arg = check_int_value(arg, 1, len(self.realms))
            if arg != -1:
                realm = self.realms[arg-1]

        if realm:
            print(f"Closing realm...")
            self.close_realm(realm)

    def do_describe(self, arg):
        """
        Print information about the current realm - optional arguments:
           realm        - print information about the realm (default)
           config       - print information about the config provided to the realm
           schema       - print the schema information for the realm
           schema.NAME  - print the schema class information for class NAME
        """
        if not self.active_realm:
            print("No realm has been opened")
        if not arg or arg == "realm":
            print(self.active_realm.info())
        elif arg == "config":
            print(self.active_realm.config.info())
        elif arg == "schema":
            class_keys = self.active_realm.get_class_keys()
            if not class_keys:
                print("No classes found")
            else:
                print(f"Schema classes: {len(class_keys)}")
                for key in class_keys:
                    info = self.active_realm.get_class(key)
                    if info:
                        print(f"- Name: {info.name.decode('ASCII')} [{RealmClassFlags(info.flags).name}]")
                        properties = self.active_realm.get_class_properties(key, info.num_properties)
                        if not properties:
                            print("  * No properties")
                        else:
                            for prop in properties:
                                print(f"  * {prop.name.decode('ASCII')}: {self.property_type(prop)}")

        elif arg.startswith("schema."):
            _, class_name = arg.split(".", 2)
            print(f"Schema class information for '{class_name}' is on the way")
        else:
            print(f"*** Invalid argument: '{arg}'")

    @classmethod
    def property_type(cls, prop: RealmPropertyInfo):
        type_stg = cls.txt_property_type(prop.type)
        if prop.type in [
            RealmPropertyType.RLM_PROPERTY_TYPE_LINKING_OBJECTS,
            RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT
        ]:
            type_stg += f"({prop.link_target.decode('ASCII') if prop.link_target else ''}"
            type_stg += f":{prop.link_origin_property_name.decode('ASCII') if prop.link_origin_property_name else ''})"
        flags = RealmPropertyFlags(prop.flags)
        if flags & RealmPropertyFlags.RLM_PROPERTY_NULLABLE:
            type_stg += "?"
        if prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_LIST:
            type_stg = f"List<{type_stg}>"
        elif prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_SET:
            type_stg = f"Set<{type_stg}>"
        elif prop.collection_type == RealmCollectionType.RLM_COLLECTION_TYPE_DICTIONARY:
            type_stg = f"Dictionary<{type_stg}>"
        return f"{type_stg}{'(primary key)' if flags & RealmPropertyFlags.RLM_PROPERTY_PRIMARY_KEY else ''}"

    @classmethod
    def txt_property_type(cls, rtype: RealmPropertyType):
        if rtype == RealmPropertyType.RLM_PROPERTY_TYPE_INT:
            return "int"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_BOOL:
            return "bool"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_STRING:
            return "string"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_BINARY:
            return "binary"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_MIXED:
            return "mixed"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_TIMESTAMP:
            return "timestamp"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_FLOAT:
            return "float"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_DOUBLE:
            return "double"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_DECIMAL128:
            return "decimal128"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT:
            return "object"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_LINKING_OBJECTS:
            return "linked_objects"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_OBJECT_ID:
            return "objectID"
        elif rtype == RealmPropertyType.RLM_PROPERTY_TYPE_UUID:
            return "UUID"
        else:
            raise ValueError(f"Property type '{rtype}' is invalid")

    def do_exit(self, _):
        'Close the realm and exit'
        print('Exiting...')
        close_realms()
        return True

    def print_realms(self, realm_list: List[Realm], active: Realm = None, prepend: str = ""):
        if realm_list:
            for i, x in enumerate(realm_list):
                if x is None:
                    print(f"{prepend}[{i+1}] - None")
                else:
                    print(f"{prepend}[{i+1}] - {str(x)}{', Active' if x == active else ''}")

    def open_realm(self, arg: str):
        path = ""
        if not arg.endswith(".realm"):
            arg = arg + ".realm"
        if os.path.exists(arg):
            path = os.path.abspath(arg)
        else:
            relpath = os.path.abspath(os.path.join(os.getcwd(), arg))
            if os.path.exists(relpath):
                path = relpath
        if not path:
            print(f"File not found: {arg}")
        else:
            try:
                config = RealmConfig(path=path)
                realm = Realm(config)
                self.realms.append(realm)
                self.active_realm = realm
                print(f"Opened realm file: {path}")
            except Exception as e:
                print(f"Error opening realm: {e}")

    def close_realm(self, realm: Realm):
        try:
            realm.close()
        except Exception as e:
            print(f"Error closing realm: {e}")
        self.realms.remove(realm)

def check_int_value(value: Any, minval: int = -1, maxval: int = -1):
    intval = -1
    error = False
    try:
        intval = int(value)
        if minval != -1 and intval < minval:
            error = True
        elif maxval != -1 and intval > maxval:
            error = True
    except Exception as e:
        print("*** Syntax error: index must be an integer value")
    if error:
        if minval != -1:
            if maxval != -1:
                error = f"between {minval} and {maxval}"
            else:
                error = f"greater than or equal to {minval}"
        elif maxval != -1:
            error = f"less than or equal to {maxval}"
        print(f"*** Index error: {error}")
    return intval




if __name__ == '__main__':
    basepath = Path().absolute()
    if len(sys.argv) > 1:
        basepath = Path(sys.argv[1])

    # Load the dynamic lib
    libpath =  basepath / "lib" / "librealm-ffi-dbg.dylib"
    print(f"Loading realm library: {str(libpath)}")
    realm_init(libpath)

    RealmDemoShell().cmdloop()
