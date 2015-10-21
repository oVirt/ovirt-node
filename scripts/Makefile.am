# Copyright (C) 2010 Red Hat, Inc.
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

localboottriggerdir=$(sysconfdir)/ovirt-config-boot.d

dist_sbin_SCRIPTS = \
  persist \
  unpersist \
  ovirt-node-upgrade.py \
  ovirt-node-update-initramfs

dist_bin_SCRIPTS = \
  ovirt-node-setup \
  ovirt-node-installer \
  ovirt-node-config-password \
  ovirt-node-doc \
  ovirt-node-features \
  ovirt-node-config

dist_libexec_SCRIPTS = \
  ovirt-config-uninstall \
  ovirt-functions \
  ovirt-init-functions.sh \
  ovirt-node-hooks.sh \
  ovirt-auto-install.py \
  ovirt-admin-shell \
  ovirt-node-igor-slave

# default hook for local_boot_trigger
dist_localboottrigger_SCRIPTS = \
  local_boot_trigger.sh

install-exec-hook:
	mv $(DESTDIR)$(libexecdir)/ovirt-auto-install.py $(DESTDIR)$(libexecdir)/ovirt-auto-install
	mv $(DESTDIR)$(sbindir)/ovirt-node-upgrade.py $(DESTDIR)$(sbindir)/ovirt-node-upgrade
	mv $(DESTDIR)$(libexecdir)/ovirt-node-hooks.sh $(DESTDIR)$(libexecdir)/ovirt-node-hooks

	mkdir -p --mode=0755 \
	  $(DESTDIR)$(localboottriggerdir) \
	  $(DESTDIR)$(sysconfdir)/node.d \
	  $(DESTDIR)$(sysconfdir)/ovirt-early.d \
	  $(DESTDIR)$(sysconfdir)/ovirt-commandline.d \
	  $(DESTDIR)$(sysconfdir)/default
	echo "# File where default configuration is kept" > $(DESTDIR)$(sysconfdir)/default/ovirt
