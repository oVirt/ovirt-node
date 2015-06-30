# -*- coding: utf-8 -*-
"""
This package contains all plugins and the __main__ for the setup application.

Each plugin can create it's own directory (a so called plugin group).
"""


def __call__(self=None, *a, **k):
    """FIXME this is a workaround to get nosetests working
    nosetests sees this module as the setup() funciton for unit tests
    This method is defined to provide a no-op
    See also: https://code.google.com/p/python-nose/issues/detail?id=326
    """
    pass
