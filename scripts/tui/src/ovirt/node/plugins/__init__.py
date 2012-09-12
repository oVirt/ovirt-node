
import os
import pkgutil
import logging

import ovirt.node.plugins

LOGGER = logging.getLogger(__name__)

def __walk_plugins():
    package = ovirt.node.plugins
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        yield (importer, modname, ispkg)


def load_all():
    modules = []
    for importer, modname, ispkg in __walk_plugins():
        #print("Found submodule %s (is a package: %s)" % (modname, ispkg))
        module = __import__("ovirt.node.plugins." + modname, fromlist="dummy")
        #print("Imported", module)
        modules += [module]
    return modules


class NodePlugin(object):
    def name(self):
        raise Exception("Not yet implemented.")

    def ui_name(self):
        return self.name()

    def ui_on_change(self, model):
        """Called when some widget was changed
        """
        LOGGER.debug("changed: " + str(model))

    def ui_on_save(self, model):
        """Called when data should be saved
        """
        LOGGER.debug("saved")


class Label(object):
    def __init__(self, label):
        self.label = label

class Entry(object):
    def __init__(self, path, label):
        self.path = path
        self.label = label
