# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import io
import os
import zipfile
from contextlib import closing
from pprint import pformat
from time import gmtime, strftime
from traceback import format_exc

from future import standard_library
standard_library.install_aliases()

from pyload.utils import sys
from pyload.utils.layer.safethreading import Thread
from types import MethodType


class PluginThread(Thread):
    """
    Abstract base class for thread types.
    """
    __slots__ = ['manager', 'owner', 'pyload']

    def __init__(self, manager, owner=None):
        Thread.__init__(self)
        self.setDaemon(True)
        self.manager = manager  #: thread manager
        self.pyload = manager.pyload
        #: Owner of the thread, every type should set it or overwrite user
        self.owner = owner

    @property
    def user(self):
        return self.owner.primary if self.owner else None

    def finished(self):
        """
        Remove thread from list.
        """
        self.manager.remove_thread(self)

    def get_progress(self):
        """
        Retrieves progress information about the current running task

        :return: :class:`ProgressInfo`
        """

    # Debug Stuff
    def write_debug_report(self, name, pyfile=None, plugin=None):
        """
        Writes a debug report to disk.
        """
        dump_name = "debug_{0}_{1}.zip".format(
            name, strftime("%d-%m-%Y_%H-%M-%S"))
        if pyfile:
            dump = self.get_plugin_dump(pyfile.plugin) + "\n"
            dump += self.get_file_dump(pyfile)
        else:
            dump = self.get_plugin_dump(plugin)

        try:
            with closing(zipfile.ZipFile(dump_name, mode='w')) as zip:
                if os.path.exists(os.path.join(
                        self.pyload.profiledir, 'crashes', 'reports', name)):
                    for f in os.listdir(os.path.join(
                            self.pyload.profiledir, 'crashes', 'reports', name)):
                        try:
                            # avoid encoding errors
                            zip.write(
                                os.path.join(self.pyload.profiledir, 'crashes', 'reports', name, f), os.path.join(
                                    name, f))
                        except Exception:
                            pass

                info = zipfile.ZipInfo(
                    os.path.join(
                        name,
                        "debug_Report.txt"),
                    gmtime())
                info.external_attr = 0o644 << 16  #: change permissions
                zip.writestr(info, dump)

                info = zipfile.ZipInfo(
                    os.path.join(
                        name,
                        "system_Report.txt"),
                    gmtime())
                info.external_attr = 0o644 << 16
                zip.writestr(info, self.get_system_dump())

            if not os.stat(dump_name).st_size:
                raise Exception("Empty Zipfile")

        except Exception as e:
            self.pyload.log.debug(
                "Error creating zip file: {0}".format(e.message))

            dump_name = dump_name.replace(".zip", ".txt")
            with io.open(dump_name, mode='wb') as fp:
                fp.write(dump)

        self.pyload.log.info(_("Debug Report written to {0}").format(dump_name))
        return dump_name

    def get_plugin_dump(self, plugin):
        dump = "pyLoad {0} Debug Report of {1} {2} \n\nTRACEBACK:\n {3} \n\nFRAMESTACK:\n".format(
            self.manager.pyload.api.get_server_version(
            ), plugin.__name__, plugin.__version__, format_exc()
        )
        tb = sys.exc_info()[2]
        stack = []
        while tb:
            stack.append(tb.tb_frame)
            tb = tb.tb_next

        for frame in stack[1:]:
            dump += "\nFrame {0} in {1} at line {2}\n".format(frame.f_code.co_name,
                                                           frame.f_code.co_filename,
                                                           frame.f_lineno)

            for key, value in frame.f_locals.items():
                dump += "\t{0:20} = ".format(key)
                try:
                    dump += pformat(value) + "\n"
                except Exception as e:
                    dump += "<ERROR WHILE PRINTING VALUE> {0}\n".format(
                        e.message)

            del frame

        del stack  #: delete it just to be sure...

        dump += "\n\nPLUGIN OBJECT DUMP: \n\n"

        for name in dir(plugin):
            attr = getattr(plugin, name)
            if not name.endswith("__") and not isinstance(attr, MethodType):
                dump += "\t{0:20} = ".format(name)
                try:
                    dump += pformat(attr) + "\n"
                except Exception as e:
                    dump += "<ERROR WHILE PRINTING VALUE> {0}\n".format(
                        e.message)

        return dump

    def get_file_dump(self, pyfile):
        dump = "PYFILE OBJECT DUMP: \n\n"

        for name in dir(pyfile):
            attr = getattr(pyfile, name)
            if not name.endswith("__") and not isinstance(attr, MethodType):
                dump += "\t{0:20} = ".format(name)
                try:
                    dump += pformat(attr) + "\n"
                except Exception as e:
                    dump += "<ERROR WHILE PRINTING VALUE> {0}\n".format(
                        e.message)

        return dump

    def get_system_dump(self):
        dump = "SYSTEM:\n\n"
        for k, v in sys.get_info().items():
            dump += "{0}: {1}\n".format(k, v)

        return dump
