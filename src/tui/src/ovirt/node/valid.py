#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# valid.py - Copyright (C) 2012 Red Hat, Inc.
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
import base
import exceptions
import os.path
import re
import socket
import subprocess
import urlparse

"""
A module with several validators for common user inputs.
"""


class Validator(base.Base):
    """This class is used to validate user inputs
    Basically an exception is raised if an invalid value was given. The value
    is validated using the self.validate(value) method raises an exception.
    This is just a base class because this class doesn't implement the actual
    validation method.

    Further below you will find an regex validator which uses regular
    expressions to validate the input.
    """
    __exception_msg = "The field must contain {description}."
    description = None

    def validate(self, value):
        """Validate a given value, return true if valid.
        This method shall just return True or False and not exception.

        Args:
            value: The value to be validated

        Returns:
            True if valid
        """
        raise Exception("To be implemented by subclass")

    def __call__(self, value):
        if not self.description:
            self.description = self.__doc__
        if not self.validate(value):
            self.raise_exception()
        return True

    def raise_exception(self):
        msg = self.__exception_msg.format(description=self.description)
        # pylint: disable-msg=E1101
        raise exceptions.InvalidData(msg)
        # pylint: enable-msg=E1101

    def __or__(self, other):
        """This allows to combin validators using |
        >>> a = RegexValidator()
        >>> a.pattern = "^a"
        >>> a.description ="a at the beginning"
        >>> b = RegexValidator()
        >>> b.pattern = "b$"
        >>> b.description ="b at the end"
        >>> a.validate("ab")
        True
        >>> b.validate("ab")
        True
        >>> b.validate("abc")
        False
        >>> (a | b).validate("abc")
        True
        >>> (a | b).validate("cb")
        True
        >>> (a | b).validate("c")
        False
        """
        this = self

        class OrValidator(Validator):
            description = " or ".join([this.description,
                                       other.description])

            def validate(self, value):
                return (this.validate(value) or other.validate(value))

        return OrValidator()

    def __and__(self, other):
        """This allows to combin validators using &
        >>> a = RegexValidator()
        >>> a.pattern = "^a"
        >>> a.description ="a at the beginning"
        >>> b = RegexValidator()
        >>> b.pattern = "b$"
        >>> b.description ="b at the end"
        >>> a.validate("ab")
        True
        >>> b.validate("ab")
        True
        >>> b.validate("abc")
        False
        >>> (a & b).validate("abc")
        False
        >>> (a & b).validate("cb")
        False
        >>> (a & b).validate("c")
        False
        >>> (a & b).validate("acb")
        True
        """
        this = self

        class AndValidator(Validator):
            description = " and ".join([this.description,
                                        other.description])

            def validate(self, value):
                return (this.validate(value) and other.validate(value))

        return AndValidator()


class RegexValidator(Validator):
    """A validator which uses a regular expression to validate a value.
    """
    # pattern defined by subclass
    pattern = None

    def __init__(self, pattern=None, description=None):
        super(RegexValidator, self).__init__()
        self.pattern = self.pattern or pattern
        self.description = self.description or description

    def validate(self, value):
        if type(self.pattern) in [str, unicode]:
            self.pattern = (self.pattern, )
        if type(value) in [bool, int]:
            value = str(value)
        elif type(value) in [str, unicode]:
            pass
        else:
            self.logger.warning("Unknown type: %s %s" % (value, type(value)))
        return value is not None and \
            re.compile(*self.pattern).search(value) is not None


class Text(RegexValidator):
    """Quite anything

    >>> Text()("anything")
    True
    >>> Text()("")
    True
    """

    description = "anything"
    pattern = ".*"

    def __init__(self, min_length=0):
        if min_length > 0:
            self.pattern = ".{%d}" % min_length
            self.description += " (min. %d chars)" % min_length


class Number(RegexValidator):
    """A number

    >>> Number()(42)
    True
    >>> Number()(-42)
    True
    >>> Number()("42")
    True
    >>> Number(bounds=[0, None]).validate(-10)
    False
    >>> Number(bounds=[0, 10]).validate(11)
    False
    >>> Number().validate("4 2")
    False
    >>> Number(exactly=42).validate("42")
    True
    >>> Number(exactly=42).validate("4")
    False
    """

    description = "a number"
    pattern = "^[-+]?\d+$"
    bounds = None

    def __init__(self, bounds=None, exactly=None):
        super(Number, self).__init__()
        if bounds:
            self.bounds = bounds
            self.description = "%s in the bounds %s" % (self.description,
                                                        bounds)
        elif exactly is not None:
            self.logger.debug("Using exact number: %s" % exactly)
            self.pattern = "^%d$" % exactly
            self.description = "%s" % (exactly)

    def validate(self, value):
        self.logger.debug("Checking number %s %s %s" % (self, self.pattern,
                                                        value))
        valid = RegexValidator.validate(self, value)
        if valid and self.bounds:
            self.logger.debug("Checking bounds: %s" % self.bounds)
            vmin, vmax = self.bounds
            value = int(value)
            if (vmin is not None and value < vmin) or \
               (vmax is not None and value > vmax):
                valid = False
        return valid


class Port(Number):
    """An TCP/UDP port number

    >>> Port()(42)
    True
    >>> Port().validate(-42)
    False
    >>> Port().validate(12345678)
    False
    """

    description = "a port number"

    def __init__(self):
        super(Port, self).__init__(bounds=[1, 65535])


class NoSpaces(RegexValidator):
    """A string, but without any space character

    >>> NoSpaces()("abc")
    True
    >>> NoSpaces().validate("a b c")
    False
    """

    description = "a string without spaces"
    pattern = "^\S+$"


class FQDN(RegexValidator):
    """Matches a FQDN

    >>> FQDN()("example.com")
    True
    >>> FQDN().validate("example")
    True
    >>> FQDN()("0.example.com")
    True
    >>> FQDN().validate("example.com.")
    False
    >>> FQDN().validate(".com")
    False
    >>> FQDN().validate("")
    False
    """

    description = "a valid FQDN"
    pattern = ("^(([0-9]\.)?([a-z]|[a-z][a-z0-9\-]*[a-z0-9])\.)*" +
               "([a-z]|[a-z][a-z0-9\-]*[a-z0-9])$", re.I)


class IPv4Address(Validator):
    """Matches IPv4 addresses

    >>> IPv4Address()("127.0.0.1")
    True
    >>> IPv4Address()("1.2.3.4")
    True
    >>> IPv4Address().validate("127.0.0.1.2")
    False
    >>> IPv4Address().validate("127.0.0.")
    False
    >>> IPv4Address().validate("")
    False
    >>> IPv4Address().validate("999.99.9.0")
    False
    """

    description = "a valid IPv4 address"
    family = socket.AF_INET

    def validate(self, value):
        valid = True
        try:
            socket.inet_pton(self.family, value)
        except:
            valid = False
        return valid


class IPv6Address(IPv4Address):
    """Validates IPv6 addresses

    >>> IPv6Address()("::1")
    True
    >>> IPv6Address()("::")
    True
    >>> IPv6Address()("0::0")
    True
    >>> IPv6Address().validate("0:::0")
    False
    >>> IPv6Address().validate("0::0::0")
    False
    """

    description = "a valid IPv6 address"
    family = socket.AF_INET6


class IPAddress(Validator):
    """Allows any IPv4 or IPv6 address

    >>> IPAddress()("127.0.0.1")
    True
    >>> IPAddress()("::1")
    True
    >>> IPAddress().validate("example.com")
    False
    >>> IPAddress().validate("")
    False
    """

    def __init__(self):
        self._validator = IPv4Address() | IPv6Address()
        self.description = self._validator.description

    def validate(self, value):
        return self._validator.validate(value)


class FQDNOrIPAddress(Validator):
    """Allows any FQDN, IPv4 or IPv6 address

    >>> FQDNOrIPAddress()("example.com")
    True
    >>> FQDNOrIPAddress()("127.0.0.1")
    True
    >>> FQDNOrIPAddress()("::1")
    True
    >>> FQDNOrIPAddress().validate("")
    False
    """

    def __init__(self):
        self._validator = FQDN() | IPAddress()
        self.description = self._validator.description

    def validate(self, value):
        return self._validator.validate(value)


class Options(Validator):
    options = None
    description = "one of: %s"

    def __init__(self, options):
        assert type(options) is list, "Options must be a list"
        self.options = options

    def validate(self, value):
        self.description = self.description % self.options
        return value in self.options


class Empty(Validator):
    description = "an empty string"

    def __init__(self, or_none=False):
        super(Empty, self).__init__()
        self.or_none = or_none

    def validate(self, value):
        return value == "" or (self.or_none and value is None)


class URL(Validator):
    description = "a valid URL"

    requires_scheme = False
    requires_netloc = False
    requires_path = True

    def validate(self, value):
        p = urlparse.urlparse(value)
        is_valid = True
        # pylint: disable-msg=E1101
        if self.requires_scheme:
            is_valid &= p.scheme != ""
        if self.requires_netloc:
            is_valid &= p.netloc != ""
        if self.requires_path:
            is_valid &= p.path != ""
        # pylint: enable-msg=E1101
        return is_valid


class Boolean(Validator):
    description = "a valid boolean (True or False)"

    def validate(self, value):
        return value in [True, False]


class IQN(RegexValidator):
    """Matches a IQN

    >>> IQN()("iqn.1994-05.com.redhat.com:6edea1b458e5")
    True
    >>> IQN().validate("")
    False
    """

    description = "a valid IQN"
    pattern = "^iqn\.(\d{4}-\d{2})\.([^:]+):"


class BlockDevice(Validator):
    """Matches if the value is a block device
    """
    description = "a valid block device"

    def validate(self, value):
        is_valid = False
        try:
            if os.path.exists(value):
                subprocess.check_call("test -b %s" % value, shell=True,
                                      close_fds=True)
                is_valid = True
        except:
            is_valid = False
        return is_valid
