#!/bin/env python

import re
import logging

import ovirt.node.plugins


logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


class RegexValidator(str):
    # pattern defined by subclass
    # description defined by subclass
    __exception_msg = "The field must contain {description}."

    def __call__(self, value):
        if re.search(self.pattern, value) == None:
            msg = self.__exception_msg.format(description=self.description)
            raise ovirt.node.plugins.InvalidData(msg)
        return True


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


class NoSpaces(RegexValidator):
    description = "a string without spaces"
    pattern = "^\S*$"


class Hostname(RegexValidator):
    description = "a valid hostname"
    pattern = ("^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)" +
               "*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$")


class IPv4Address(RegexValidator):
    description = "a valid IPv4 address"
    pattern = ("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)" +
               "{3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")


class IPv6Address(RegexValidator):
    description = "a valid IPv6 address"
    pattern = ("/^(?>(?>([a-f0-9]{1,4})(?>:(?1)){7}|(?!(?:.*[a-f0-9](?>:|$" +
               ")){7,})((?1)(?>:(?1)){0,5})?::(?2)?)|(?>(?>(?1)(?>:(?1)){5}" +
               ":|(?!(?:.*[a-f0-9]:){5,})(?3)?::(?>((?1)(?>:(?1)){0,3}):)?)?" +
               "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])(?>\.(?" +
               "4)){3}))$/iD")


class OrCombinedValidator(str):
    _validators = None

    def __init__(self, validators):
        self._validators = validators

    def __call__(self, value):
        is_valid = False
        msgs = []

        for v in self._validators:
            LOGGER.debug(v)
            try:
                msg = v(value)
                if msg:
                    msgs.append(msg)
                else:
                    is_valid = True
                    break
            except ovirt.node.plugins.InvalidData as e:
                msgs.append(str(e))

        if not is_valid:
            msg = ", ".join(msgs)
            raise ovirt.node.plugins.InvalidData(msg)

        return True
