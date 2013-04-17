# Copyright (C) 2013 Red Hat, Inc.
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

pyovirtconfigsetupdir =$(pythondir)/ovirt_config_setup
pyovirtconfigsetup_PYTHON = \
  ovirt_config_setup/__init__.py \
  ovirt_config_setup/plugins.py

if TARGET_FEDORA
pyovirtconfigsetup_PYTHON += \
  ovirt_config_setup/collectd.py
endif

if TARGET_CENTOS
pyovirtconfigsetup_PYTHON += \
  ovirt_config_setup/collectd.py
endif

if TARGET_RHEL
pyovirtconfigsetup_PYTHON += \
  ovirt_config_setup/rhn.py
endif

pyovirtnodedir = $(pythondir)/ovirtnode
pyovirtnode_PYTHON = \
  ovirtnode/__init__.py \
  ovirtnode/install.py \
  ovirtnode/iscsi.py \
  ovirtnode/kdump.py \
  ovirtnode/log.py \
  ovirtnode/network.py \
  ovirtnode/ovirtfunctions.py \
  ovirtnode/password.py \
  ovirtnode/storage.py

pyovirtdir = $(pythondir)/ovirt
pyovirt_nodedir = $(pyovirtdir)/node
pyovirt_node_configdir = $(pyovirt_nodedir)/config
pyovirt_node_installerdir = $(pyovirt_nodedir)/installer
pyovirt_node_setupdir = $(pyovirt_nodedir)/setup
pyovirt_node_uidir = $(pyovirt_nodedir)/ui
pyovirt_node_utilsdir = $(pyovirt_nodedir)/utils

pyovirt_PYTHON = \
  ovirt/__init__.py

pyovirt_node_PYTHON = \
  ovirt/node/__init__.py \
  ovirt/node/exceptions.py \
  ovirt/node/plugins.py \
  ovirt/node/valid.py \
  ovirt/node/app.py \
  ovirt/node/base.py

pyovirt_node_config_PYTHON = \
  ovirt/node/config/defaults.py \
  ovirt/node/config/__init__.py \
  ovirt/node/config/network.py

pyovirt_node_installer_PYTHON = \
  ovirt/node/installer/__init__.py \
  ovirt/node/installer/__main__.py \
  ovirt/node/installer/boot_device_page.py \
  ovirt/node/installer/installation_device_page.py \
  ovirt/node/installer/keyboard_page.py \
  ovirt/node/installer/password_page.py \
  ovirt/node/installer/progress_page.py \
  ovirt/node/installer/storage_vol_page.py \
  ovirt/node/installer/upgrade_page.py \
  ovirt/node/installer/welcome_page.py

pyovirt_node_setup_PYTHON = \
  ovirt/node/setup/__init__.py \
  ovirt/node/setup/__main__.py \
  ovirt/node/setup/kdump_page.py \
  ovirt/node/setup/keyboard_page.py \
  ovirt/node/setup/logging_page.py \
  ovirt/node/setup/monitoring_page.py \
  ovirt/node/setup/network_page.py \
  ovirt/node/setup/ping.py \
  ovirt/node/setup/remote_storage_page.py \
  ovirt/node/setup/security_page.py \
  ovirt/node/setup/snmp_page.py \
  ovirt/node/setup/status_page.py \
  ovirt/node/setup/support_page.py

pyovirt_node_ui_PYTHON = \
  ovirt/node/ui/__init__.py \
  ovirt/node/ui/urwid_builder.py \
  ovirt/node/ui/widgets.py

pyovirt_node_utils_PYTHON = \
  ovirt/node/utils/__init__.py \
  ovirt/node/utils/console.py \
  ovirt/node/utils/fs.py \
  ovirt/node/utils/network.py \
  ovirt/node/utils/process.py \
  ovirt/node/utils/security.py \
  ovirt/node/utils/storage.py \
  ovirt/node/utils/system.py \
  ovirt/node/utils/virt.py


# Requires python-pep8 package (Fedora)
check-local: check-local-pep8

check-local-pep8:
	find $(srcdir) -name \*.py | sort | uniq | xargs pep8 --repeat --statistics --count

check-local-doctest:
	find $(srcdir) -name \*.py | sort | uniq | xargs python -m doctest -v
