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

include Makefile.check

PYTHONSOURCES:=$(shell find . -wholename ./ovirt/\*.py)
XMLSOURCES:=$(shell find . -name \*.xml -or -name \*.xsl)
CLEANFILES:=$(shell find . -name \*.pyc -o -name \*.pyo -o -name \*~ -o -name MANIFEST)

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

# Basic dirs
pyovirtdir = $(pythondir)/ovirt
pyovirt_nodedir = $(pyovirtdir)/node
pyovirt_node_configdir = $(pyovirt_nodedir)/config
ovirt_node_locale_cndir = /usr/share/locale/zh_CN/LC_MESSAGES
ovirt_node_locale_endir = /usr/share/locale/en_US/LC_MESSAGES
pyovirt_node_uidir = $(pyovirt_nodedir)/ui
pyovirt_node_utilsdir = $(pyovirt_nodedir)/utils
pyovirt_node_toolsdir = $(pyovirt_nodedir)/tools

# Path to installer app and installer plugins
pyovirt_node_installerdir = $(pyovirt_nodedir)/installer
pyovirt_node_installer_coredir = $(pyovirt_node_installerdir)/core

# Path to setup app and setup plugins
pyovirt_node_setupdir = $(pyovirt_nodedir)/setup
pyovirt_node_setup_coredir = $(pyovirt_node_setupdir)/core

# Paths to CIM and SNMP setup plugins
pyovirt_node_setup_cimdir = $(pyovirt_node_setupdir)/cim
pyovirt_node_setup_snmpdir = $(pyovirt_node_setupdir)/snmp
pyovirt_node_setup_puppetdir = $(pyovirt_node_setupdir)/puppet
pyovirt_node_setup_ipmidir = $(pyovirt_node_setupdir)/ipmi


pyovirt_PYTHON = \
  ovirt/__init__.py

pyovirt_node_PYTHON = \
  ovirt/node/__init__.py \
  ovirt/node/exceptions.py \
  ovirt/node/plugins.py \
  ovirt/node/valid.py \
  ovirt/node/app.py \
  ovirt/node/base.py \
  ovirt/node/loader.py \
  ovirt/node/log.py

dist_ovirt_node_locale_cn_DATA = \
  ovirt/node/locale/zh_CN/LC_MESSAGES/ovirt_node.mo

dist_ovirt_node_locale_en_DATA = \
  ovirt/node/locale/en_US/LC_MESSAGES/ovirt_node.mo


pyovirt_node_config_PYTHON = \
  ovirt/node/config/__init__.py \
  ovirt/node/config/defaults.py \
  ovirt/node/config/migrate.py \
  ovirt/node/config/network.py \
  ovirt/node/config/tuned.py

pyovirt_node_ui_PYTHON = \
  ovirt/node/ui/__init__.py \
  ovirt/node/ui/urwid_builder.py \
  ovirt/node/ui/widgets.py

pyovirt_node_utils_PYTHON = \
  ovirt/node/utils/__init__.py \
  ovirt/node/utils/console.py \
  ovirt/node/utils/expose.py \
  ovirt/node/utils/firewall.py \
  ovirt/node/utils/fs.py \
  ovirt/node/utils/network.py \
  ovirt/node/utils/process.py \
  ovirt/node/utils/security.py \
  ovirt/node/utils/storage.py \
  ovirt/node/utils/system.py \
  ovirt/node/utils/tuned.py \
  ovirt/node/utils/virt.py \
  ovirt/node/utils/input.py

pyovirt_node_tools_PYTHON = \
  ovirt/node/tools/__init__.py \
  ovirt/node/tools/password.py \
  ovirt/node/tools/features.py

dist_pyovirt_node_tools_DATA = \
  ovirt/node/tools/featured.xsl

# Installer Main
pyovirt_node_installer_PYTHON = \
  ovirt/node/installer/__init__.py \
  ovirt/node/installer/__main__.py

# Installer Core plugins
pyovirt_node_installer_core_PYTHON = \
  ovirt/node/installer/core/__init__.py \
  ovirt/node/installer/core/boot_device_page.py \
  ovirt/node/installer/core/installation_device_page.py \
  ovirt/node/installer/core/keyboard_page.py \
  ovirt/node/installer/core/password_page.py \
  ovirt/node/installer/core/progress_page.py \
  ovirt/node/installer/core/storage_vol_page.py \
  ovirt/node/installer/core/upgrade_page.py \
  ovirt/node/installer/core/welcome_page.py


# Setup Main
pyovirt_node_setup_PYTHON = \
  ovirt/node/setup/__init__.py \
  ovirt/node/setup/__main__.py

# Setup Core Plugins
pyovirt_node_setup_core_PYTHON = \
  ovirt/node/setup/core/__init__.py \
  ovirt/node/setup/core/diagnostics_page.py \
  ovirt/node/setup/core/kdump_page.py \
  ovirt/node/setup/core/keyboard_page.py \
  ovirt/node/setup/core/logging_page.py \
  ovirt/node/setup/core/network_page.py \
  ovirt/node/setup/core/performance_page.py \
  ovirt/node/setup/core/ping.py \
  ovirt/node/setup/core/plugins_page.py \
  ovirt/node/setup/core/remote_storage_page.py \
  ovirt/node/setup/core/security_page.py \
  ovirt/node/setup/core/status_page.py \
  ovirt/node/setup/core/support_page.py

if TARGET_FEDORA
pyovirt_node_setup_core_PYTHON += \
  ovirt/node/setup/core/monitoring_page.py
endif

if TARGET_CENTOS
pyovirt_node_setup_core_PYTHON += \
  ovirt/node/setup/core/monitoring_page.py
endif


# Setup CIM Plugin
pyovirt_node_setup_cim_PYTHON = \
  ovirt/node/setup/cim/__init__.py \
  ovirt/node/setup/cim/cim_page.py \
  ovirt/node/setup/cim/cim_model.py


# Setup SNMP Plugin
pyovirt_node_setup_snmp_PYTHON = \
  ovirt/node/setup/snmp/__init__.py \
  ovirt/node/setup/snmp/snmp_page.py \
  ovirt/node/setup/snmp/snmp_model.py


# Setup Puppet Plugin
pyovirt_node_setup_puppet_PYTHON = \
  ovirt/node/setup/puppet/__init__.py \
  ovirt/node/setup/puppet/puppet_page.py


# Setup ipmi Plugin
pyovirt_node_setup_ipmi_PYTHON = \
  ovirt/node/setup/ipmi/__init__.py \
  ovirt/node/setup/ipmi/ipmi_page.py
