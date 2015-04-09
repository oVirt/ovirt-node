# Copyright (C) 2015 Red Hat, Inc.
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

onbootdir = $(libexecdir)/ovirt-node/hooks/on-boot
onshutdowndir = $(libexecdir)/ovirt-node/hooks/on-shutdown

dist_onboot_SCRIPTS = \
	on-boot/03-validate-owner-ssh-keys \
	$(NULL)

dist_onshutdown_SCRIPTS = \
	on-shutdown/01-save-virtwho.py

install-data-hook:
	mv $(DESTDIR)$(libexecdir)/ovirt-node/hooks/on-shutdown/01-save-virtwho.py \
		$(DESTDIR)$(libexecdir)/ovirt-node/hooks/on-shutdown/01-save-virtwho
