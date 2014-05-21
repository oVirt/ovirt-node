#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# ovirt-node-registration.py - Copyright (C) 2014 Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
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
import requests
import json
import logging
import sys
from optparse import OptionParser
from ovirt.node.utils import AugeasWrapper, fs, process

"""
oVirt Node Generic Registration
"""


class Client:
    """ A simple class to map json to functions and execute.

        All functions take unlimited arguments for string formatting
        and other execution, but have one or two required arguments
        for basic operation.
    """
    parameters = {}

    def __init__(self, json_data, logger=None):
        if not logger:
            logging.basicConfig(
                filename="/tmp/ovirt-node-registration.log",
                filemode='a',
                format='%(levelname)10s %(asctime)s '
                       '%(pathname)s:%(lineno)s:%(funcName)s %(message)s',
                level=logging.DEBUG
                )
            self.logger = logging.getLogger('ovirt-node-registration')
        else:
            self.logger = logger

        # A list of actions possible and their associated functions
        self.maps = {"get": self.get,
                     "ui": self.ui,
                     "persist": self.persist,
                     "exec": self.run}

        self.data = json.loads(open(json_data).read())

    def perform(self, action, params=None):
        """ Executes the steps necessary to complete a given action
            required parameters: action
        """

        for x in self.data[action]["steps"]:
            args = x["parameters"] if x["parameters"] else {}
            if params:
                args.update(params)
            self.maps[x["action"]](**args)

    def get(self, *args, **kwargs):
        """ GETs a URL, optionally stores it as {filename}
            required parameter: url
        """

        if "url" not in kwargs:
            raise RuntimeError("A url is required for get()!")

        url = kwargs["url"].format(**kwargs)
        self.logger.debug("Getting %s" % url)
        if "filename" in kwargs:
            if not kwargs["filename"].startswith("/tmp"):
                self.persist(file=kwargs["filename"])
            with open(kwargs["filename"], "w") as f:
                response = requests.get(url, stream=True)
                if response.ok:
                    for chunk in response.iter_content():
                        f.write(chunk)
                else:
                    self.logger.info("Failed to get %s" % url)
        else:
            r = requests.get(url)
            if not r.ok:
                self.logger.info("Failed to get %s" % url)

    def ui(self, *args, **kwargs):
        """ Sets a value in /etc/default/ovirt for the TUI to read
            required parameters: key, value
        """

        if "key" not in kwargs or "value" not in kwargs:
            raise RuntimeError("A key and value are required to prompt "
                               "for UI interaction")
        aug = AugeasWrapper()
        aug.set("/files/etc/default/ovirt/%s" % kwargs["key"],
                kwargs["value"])

    def persist(self, *args, **kwargs):
        """ Persists a file
            required parameter: file
        """

        if "file" not in kwargs:
            raise RuntimeError("A file is required for persist()!")

        self.logger.debug("Persisting %s" % kwargs["file"])
        fs.Config().persist(kwargs["file"])

    def run(self, *args, **kwargs):
        """ Executes a commmand
            required parameter: cmd
        """

        if "cmd" not in kwargs:
            raise RuntimeError("A command is required for exec()!")

        cmd = kwargs["cmd"].format(**kwargs)

        self.logger.debug("Running %s" % cmd)
        output = process.check_output(cmd, shell=True)
        self.logger.debug("Output of %s was: %s" % cmd, output)


def main():
    usage = "usage: %prog -a {action} -p foo=bar,x=y filename.json"
    parser = OptionParser(usage=usage)
    parser.add_option("-a", "--action", dest="action",
                      help="action to execute")
    parser.add_option("-p", "--params", dest="params",
                      help="list of comma-separated parameters in the form "
                      "of 'foo=bar,x=y'")
    (options, args) = parser.parse_args()

    params = {}

    if options.params:
        for x in options.params.split(","):
            params[x.split('=')[0]] = x.split('=')[1]

    if len(args) < 1:
        print "Must provide a filename!"
        sys.exit(1)

    c = Client(args[0])
    c.perform(options.action, params)

if __name__ == "__main__":
    main()
