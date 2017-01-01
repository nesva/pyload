#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
import re
import inspect
from os.path import abspath, dirname, join

path = dirname(abspath(__file__))
root = abspath(join(path, "..", ".."))

from thrift.Thrift import TType
from thriftgen.pyload import ttypes
from thriftgen.pyload import Pyload

from pyload import info

type_map = {
    TType.BOOL: 'bool',
    TType.DOUBLE: 'float',
    TType.I16: 'int',
    TType.I32: 'int',
    TType.I64: 'int',
    TType.STRING: 'str',
    TType.MAP: 'dict',
    TType.LIST: 'list',
    TType.SET: 'set',
    TType.VOID: 'None',
    TType.STRUCT: 'BaseObject',
    TType.UTF8: 'unicode',
}

def get_spec(spec, optional=False):
    """ analyze the generated spec file and writes information into file """
    if spec[1] == TType.STRUCT:
        return spec[3][0].__name__
    elif spec[1]  == TType.LIST:
        if spec[3][0] == TType.STRUCT:
            ttype = spec[3][1][0].__name__
        else:
            ttype = type_map[spec[3][0]]
        return "(list, {})".format(ttype)
    elif spec[1] == TType.MAP:
        if spec[3][2] == TType.STRUCT:
            ttype = spec[3][3][0].__name__
        else:
            ttype = type_map[spec[3][2]]

        return "(dict, {}, {})".format(type_map[spec[3][0]], ttype)
    else:
        return type_map[spec[1]]

optional_re = "{:d}: +optional +[a-z0-9<>_-]+ +{}"

def main():

    enums = []
    classes = []
    tf = open(join(path, "pyload.thrift"), "rb").read()

    print("generating apitypes.py")

    for name in dir(ttypes):
        klass = getattr(ttypes, name)

        if name in ("TBase", "TExceptionBase") or name.startswith("_") or not (issubclass(klass, ttypes.TBase) or issubclass(klass, ttypes.TExceptionBase)):
            continue

        if hasattr(klass, "thrift_spec"):
            classes.append(klass)
        else:
            enums.append(klass)


    f = open(join(path, "apitypes.py"), "wb")
    f.write(
        """# -*- coding: utf-8 -*-
# Autogenerated by pyload
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING


class BaseObject(object):
\t__version__ = {0}
\t__slots__ = []

\tdef __str__(self):
\t\treturn "<{} {}>".format(self.__class__.__name__, ", ".join("{}={}".format(k, getattr(self,k)) for k in self.__slots__))


class ExceptionObject(Exception):
\t__version__ = {0}
\t__slots__ = []

""".format(info().version))

    dev = open(join(path, "apitypes_debug.py"), "wb")
    dev.write("""# -*- coding: utf-8 -*-
# Autogenerated by pyload
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING\n
from apitypes import *\n
""")

    dev.write("enums = [\n")

    ## generate enums
    for enum in enums:
        name = enum.__name__
        f.write("class {}:\n".format(name))

        for attr in sorted(dir(enum), key=lambda x: getattr(enum, x)):
            if attr.startswith("_") or attr in ("read", "write"):
                continue
            f.write("\t{} = {}\n".format(attr, getattr(enum, attr)))

        dev.write('\t"{}",\n'.format(name))
        f.write("\n")

    dev.write("]\n\n")

    dev.write("classes = {\n")

    for klass in classes:
        name = klass.__name__
        base = "ExceptionObject" if issubclass(klass, ttypes.TExceptionBase) else "BaseObject"
        f.write("class {}({}):\n".format(name, base))

        # No attributes, don't write further info
        if not klass.__slots__:
            f.write("\tpass\n\n")
            continue

        f.write("\t__slots__ = {}\n\n".format(klass.__slots__))
        dev.write("\t'{}' : [".format(name))

        #create init
        args = ['self'] + ["{}=None".format(x) for x in klass.__slots__]
        specs = []

        f.write("\tdef __init__({}):\n".format(", ".join(args)))
        for i, attr in enumerate(klass.__slots__):
            f.write("\t\tself.{} = {}\n".format(attr, attr))

            spec = klass.thrift_spec[i+1]
            # assert correct order, so the list of types is enough for check
            assert spec[2] == attr
            # dirty way to check optional attribute, since it is not in the generated code
            # can produce false positives, but these are not critical
            optional = re.search(optional_re.format(i + 1, attr), tf, re.I)
            if optional:
                specs.append("(None, {})".format(get_spec(spec)))
            else:
                specs.append(get_spec(spec))

        f.write("\n")
        dev.write(", ".join(specs) + "],\n")

    dev.write("}\n\n")

    f.write("class Iface(object):\n")
    dev.write("methods = {\n")

    for name in dir(Pyload.Iface):
        if name.startswith("_"):
            continue

        func = inspect.getargspec(getattr(Pyload.Iface, name))

        f.write("\tdef {}({}):\n\t\tpass\n".format(name, ", ".join(func.args)))

        spec = getattr(Pyload, "{}_result".format(name)).thrift_spec
        if not spec or not spec[0]:
            dev.write("\t'{}': None,\n".format(name))
        else:
            spec = spec[0]
            dev.write("\t'{}': {},\n".format(name, get_spec(spec)))

    f.write("\n")
    dev.write("}\n")

    f.close()
    dev.close()

if __name__ == "__main__":
    main()
