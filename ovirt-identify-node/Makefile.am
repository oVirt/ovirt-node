# Copyright (C) 2008 Red Hat, Inc.
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

bin_PROGRAMS = ovirt-identify-node

EXTRA_DIST = AUTHOR

ovirt_identify_node_SOURCES = \
  ovirt-identify-node.h \
  comm.c \
  gather.c \
  hal_support.c \
  main.c \
  protocol.c

ovirt_identify_node_LDADD = \
  $(LDADD) $(DBUS_LIBS) $(HAL_LIBS) $(VIRT_LIBS)
ovirt_identify_node_CPPFLAGS = \
  $(AM_CPPFLAGS) $(DBUS_CFLAGS) $(HAL_CFLAGS) $(VIRT_CFLAGS)
