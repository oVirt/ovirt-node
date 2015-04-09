#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# 01-save-virtwho - Copyright (C) 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
from glob import glob
from ovirt.node.utils.fs import Config


if __name__ == "__main__":
    try:
        Config().persist("/etc/virt-who.d/")
    except:
        "Couldn't persist %s!" % "/etc/virt-who.d"
        raise
