"""
A module with several validators for common user inputs.
"""
import re
import logging
import socket
import urlparse

import ovirt.node.plugins


logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


class Validator(object):
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
        raise ovirt.node.plugins.InvalidData(msg)

class RegexValidator(Validator):
    """A validator which uses a regular expression to validate a value.
    """
    # pattern defined by subclass

    def validate(self, value):
        if type(self.pattern) in [str, unicode]:
            self.pattern = (self.pattern, )
        return re.compile(*self.pattern).search(str(value)) != None


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
    >>> Number().validate("4 2")
    False
    """

    description = "a number"
    pattern = "^[-]?\d+$"
    minmax = (None, None)

    def __init__(self, min=None, max=None):
        if min or max:
            self.minmax = (min, max)
            self.description = "%s (%s - %s)" % (self.description, min, max)

    def validate(self, value):
        valid = RegexValidator.validate(self, value)
        if valid:
            min, max = self.minmax
            value = int(value)
            if (min and value < min) or (max and value > max):
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
        super(Port, self).__init__(1, 65535)


class NoSpaces(RegexValidator):
    """A string, but without any space character

    >>> NoSpaces()("abc")
    True
    >>> NoSpaces().validate("a b c")
    False
    """

    description = "a string without spaces"
    pattern = "^\S*$"


class FQDN(RegexValidator):
    """Matches a FQDN

    >>> FQDN()("example.com")
    True
    >>> FQDN().validate("example.com.")
    False
    >>> FQDN().validate("")
    False
    """

    description = "a valid FQDN"
    pattern = ("^(([a-z]|[a-z][a-z0-9\-]*[a-z0-9])\.)" +
               "*([a-z]|[a-z][a-z0-9\-]*[a-z0-9])$", re.I)


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

    description = " or ".join([FQDN.description, IPv4Address.description,
                               IPv6Address.description])

    def validate(self, value):
        return (FQDN().validate(value) or \
                IPv4Address().validate(value) or \
                IPv6Address().validate(value))


class Options(Validator):
    options = None
    description = "one of: %s"

    def __init__(self, options):
        assert type(options) is list, "Options must be a list"
        self.options = options

    def validate(self, value):
        self.description = self.description % self.options
        return value in self.options
