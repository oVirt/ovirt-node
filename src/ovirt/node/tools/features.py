#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# ovirt-node-setup.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import loader, setup
from ovirt.node.utils.expose import Property, Registry, XmlBuilder, Owner
from ovirt.node.utils.system import SystemRelease
import logging
import os.path
import sys


"""
An example daemon publishing the features of the plugins via http
The published format is XML.

You can use a e.g.
curl (to view the raw xml file):  curl http://localhost:8082/
or a webbrowser (more fancy):     xdg-open http://localhost:8082/
to view the page.
"""


def launch_bottle(registry):
    import bottle

    # Create a bottle instance and register some routes
    app = bottle.Bottle()

    xmlbuilder = XmlBuilder()
    xmlbuilder.xslt_url = "/featured.xsl"

    @app.route(xmlbuilder.xslt_url)
    def xslt():
        bottle.response.headers['Content-Type'] = 'application/xml'
        fn = os.path.dirname(__file__) + "/featured.xsl"
        print fn, __file__
        with open(fn) as src:
            return src.read()

    @app.route("/")
    def index():
        """Show the complete registry
        """
        bottle.response.headers['Content-Type'] = 'application/xml'
        return xmlbuilder.build(registry)

    @app.route("/methods/<path:path>")
    def call_method(path):
        """Call some method offered by the registry
        """
        bottle.response.headers['Content-Type'] = 'application/xml'
        kwargs = dict(bottle.request.query.items())
        return xmlbuilder.build(registry.methods[path](**kwargs))

    bottle.run(app, host='0.0.0.0', port=8082, reloader=True, debug=True)


class CpeProperty(Property):
    description = "This feature represents the CPE of this product"
    name = "version"
    namespace = "cpe"
    value = SystemRelease().cpe()


if __name__ == "__main__":
    # Create a feature registry
    registry = Registry()

    # Statically register a feature which represents the version
    registry.register(CpeProperty(owner=Owner(name=__name__)))

    # Now go through all plugins and see if they want to publish sth too
    groups = loader.plugin_groups_iterator(setup, "createPluginFeatures")
    for group, createPluginFeatures in groups:
        if createPluginFeatures:
            logging.info("Registering feature from %s" % group)
            createPluginFeatures(registry)

    # The registry is now build time to publish it

    if "-d" in sys.argv:
        # Via a http daemon
        launch_bottle(registry)
    elif "dumpxml" in sys.argv:
        # In XML to stdout
        xmlbuilder = XmlBuilder()
        print(xmlbuilder.build(registry))
    else:
        print("Get a feature summary about this node.")
        print("Usage: %s [-d] [dumpxml]" % sys.argv[0])
        sys.exit(1)
