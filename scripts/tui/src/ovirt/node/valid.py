#!/bin/env python

import re
import logging
import socket

import ovirt.node.plugins


logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


class Validator(object):
    __exception_msg = "The field must contain {description}."
    description = None

    def validate(self, value):
        """Validate a given value, return true if valid.

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
        raise ovirt.node.plugins.InvalidData(msg)

class RegexValidator(Validator):
    # pattern defined by subclass

    def validate(self, value):
        if type(self.pattern) in [str, unicode]:
            self.pattern = (self.pattern, )
        return re.compile(*self.pattern).search(value) != None


class Text(RegexValidator):
    description = "anything"
    pattern = ".*"

    def __init__(self, min_length=0):
        if min_length > 0:
            self.pattern = ".{%d}" % min_length
            self.description += " (min. %d chars)" % min_length


class Number(RegexValidator):
    description = "a number"
    pattern = "^\d+$"
    minmax = None

    def __init__(self, min=None, max=None):
        if min or max:
            self.minmax = (min, max)
            self.description = "a number (%s<%s)" % (min, max)

    def validate(self, value):
        valid = True
        RegexValidator.validate(self, value)
        try:
            value = int(value)
            LOGGER.debug("val %d" % value)
            min, max = self.minmax
            if min and value < min:
                LOGGER.debug("min %s" % min)
                self.raise_exception()
            if max and value > max:
                LOGGER.debug("max %s" % max)
                self.raise_exception()
        except:
            valid = False
        return valid

class NoSpaces(RegexValidator):
    description = "a string without spaces"
    pattern = "^\S*$"


class FQDN(RegexValidator):
    description = "a valid FQDN"
    pattern = ("^(([a-z]|[a-z][a-z0-9\-]*[a-z0-9])\.)" +
               "*([a-z]|[a-z][a-z0-9\-]*[a-z0-9])$", re.I)


class IPv4Address(Validator):
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
    description = "a valid IPv6 address"
    family = socket.AF_INET6


class FQDNOrIPAddress(Validator):
    """Allows any FQDN, IPv4 or IPv6 address
    """
    description = " or ".join([FQDN.description, IPv4Address.description,
                               IPv6Address.description])

    def validate(self, value):
        return (FQDN().validate(value) or \
                IPv4Address().validate(value) or \
                IPv6Address().validate(value))
