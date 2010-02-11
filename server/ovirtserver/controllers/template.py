# Copyright (C) 2010, Red Hat, Inc.
# Written by Darryl L. Pierce
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""Fallback controller."""

from ovirtserver.lib.base import BaseController

__all__ = ['TemplateController']


class TemplateController(BaseController):
    """
    The fallback controller for server.

    By default, the final controller tried to fulfill the request
    when no other routes match. It may be used to display a template
    when all else fails, e.g.::

        def view(self, url):
            return render('/%s' % url)

    Or if you're using Mako and want to explicitly send a 404 (Not
    Found) response code when the requested template doesn't exist::

        import mako.exceptions

        def view(self, url):
            try:
                return render('/%s' % url)
            except mako.exceptions.TopLevelLookupException:
                abort(404)

    """

    def view(self, url):
        """Abort the request with a 404 HTTP status code."""
        abort(404)
