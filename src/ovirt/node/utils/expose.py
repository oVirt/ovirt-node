#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# expose.py - Copyright (C) 2014 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.
from lxml import etree
from ovirt.node import base


class Owner(base.Base):
    """Represents a feature or method owner
    """
    name = None

    def __init__(self, name):
        self.name = name


class OwnedObject(base.Base):
        """Super-class of a feature or method

        Properties:
            name: Name of the Property/Method
            owner: Owner object pointing to the owner (plugin)
            version: just to provide a versione dinterface
            namespace: The namespace where this object shall appear in
            description: A short description of this object
            documentation: A lengthy documentation - by default the doctext
        """
        name = None
        owner = None
        version = None
        namespace = None
        description = None
        documentation = None

        def __init__(self, **kwargs):
            super(OwnedObject, self).__init__()
            for k, v in kwargs.items():
                if any(k in t.__dict__ for t in type(self).mro()):
                    self.__dict__[k] = v
            self.namespace = self.namespace or self.owner.name

        def path(self):
            """The path to this object is <path>/<name>
            """
            return "%s/%s" % (self.namespace, self.name)


class Property(OwnedObject):
    """Represents a property
    Can be seen like a boolean by default True if present,
    otherwise False.

    Members:
        value: (optional) Value for this property
    """
    value = None


class Feature(Property):
    """Like a property, but high-level
    """
    pass


class Method(OwnedObject):
    """Represents a Method

    Arguments:
        func: The function which shall be called upon invokation
    """
    func = None

    @property
    def arguments(self):
        """Return sthe arguments of self.func (without self)
        """
        varnames = list(self.func.func_code.co_varnames)
        return varnames[1:] if varnames[0] == "self" else varnames

    class Result(base.Base):
        """An object to describe the results of the function call
        """
        retval = None
        exception = None

    def __call__(self, **kwargs):
        if sorted(kwargs.keys()) != sorted(self.arguments):
            raise RuntimeError("%s vs %s" % (kwargs.keys(), self.arguments))
        result = Method.Result()
        try:
            # pylint: disable-msg=E1102
            result.retval = self.func(**kwargs)
            # pylint: enable-msg=E1102
        except Exception as e:
            result.exception = e
        return result


class Namespaces(base.Base):
    """A class to organize Objects which reside in namespaces
    But the namespace is part of the object, and not a property of container.
    This class ensures that only
    """
    items = None

    def __init__(self):
        self.items = set()

    def __find(self, path):
        """Find the item with path <path> in items
        Returns:
            None if no item with this path was found.
            Otherwise the item with the given path.
        """
        for item in self.items:
            if item.path() == path:
                return item
        return None

    def __contains__(self, path):
        """Check if an item with the path <path> is already known
        """
        return self.__find(path) is not None

    def __getitem__(self, path):
        """Get the item with the path <path> or raise a KeyError
        """
        if not path in self:
            raise KeyError
        return self.__find(path)

    def add(self, item):
        """Add an item and ensure that no other item with that namespace exists
        """
        candidate = self.__find(item.path())
        if candidate and candidate != item:
            raise KeyError("An item with this path already exists: %s" %
                           item.path())
        return self.items.add(item)

    def remove(self, item):
        """Remove an item
        """
        self.items.remove(item)

    def __iter__(self):
        """Iter through all items in all namespaces
        """
        for item in self.items:
            yield item


class Registry(base.Base):
    features = Namespaces()
    methods = Namespaces()

    def register(self, oobj):
        if issubclass(type(oobj), Property):
            self.features.add(oobj)
        elif issubclass(type(oobj), Method):
            self.methods.add(oobj)
        else:
            raise RuntimeError("Can not register object: %s" % oobj)


class XmlBuilder(base.Base):
    """Build XML for the objects of a Registry is used to provide an XML API
    """
    root = None
    xslt_url = None

    def build(self, registry):
        self.root = etree.Element("node", {"version": "0.1"})
        if self.xslt_url:
            pi = etree.PI('xml-stylesheet', 'type="text/xsl" href="%s"' %
                          self.xslt_url)
            self.root.addprevious(pi)
        if issubclass(type(registry), Registry):
            self.build_features(registry.features)
            self.build_methods(registry.methods)
        elif isinstance(registry, Method.Result):
            self.build_result(registry)
        else:
            raise RuntimeError("Can not build XML for object: %s" % registry)
        return etree.tostring(self.root.getroottree(), pretty_print=True,
                              xml_declaration=True,
                              encoding='utf-8')

    def _build_ownedobject(self, parent, tag, obj, attrs={}, text=None):
        attrs.update({"owner": obj.owner.name,
                      "namespace": obj.namespace,
                      "version": obj.version or "",
                      "description": obj.description or ""})
        element = etree.SubElement(parent, tag, attrs)
        element.text = text
        doc = obj.documentation
        doc = doc or (obj.__doc__
                      if (obj.__doc__ not in [Property.__doc__,
                                              Feature.__doc__,
                                              Method.__doc__,
                                              Method.Result.__doc__]) else "")
        if doc:
            docnode = etree.SubElement(element, "documentation")
            docnode.text = doc
        return element

    def build_features(self, features):
        subroot = etree.SubElement(self.root, "features")
        for feature in features:
            attrs = {"name": feature.name}
            self._build_ownedobject(subroot, "feature", feature, attrs,
                                    feature.value)

    def build_methods(self, methods):
        subroot = etree.SubElement(self.root, "methods")
        for method in methods:
            methodroot = self._build_ownedobject(subroot, "method", method,
                                                 {"name": method.name})
            argumentsroot = etree.SubElement(methodroot, "arguments")
            for position, argument in enumerate(method.arguments):
                etree.SubElement(argumentsroot, "argument",
                                 {"position": str(position),
                                  "name": argument})

    def build_result(self, result):
        root = etree.SubElement(self.root, "method")
        res = etree.SubElement(root, "result",
                               {"success": "success"} if not result.exception
                               else {})
        retval = etree.SubElement(res, "retval",
                                  {"type": type(result.retval).__name__})
        retval.text = bytes(result.retval)
        exception = etree.SubElement(res, "exception",
                                     {"type":
                                      type(result.exception).__name__
                                      if result.exception else ""})
        exception.text = bytes(result.exception or "")
