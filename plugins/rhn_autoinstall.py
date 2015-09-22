#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# rhn_model.py - Copyright (C) 2013 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
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

from ovirt.node.utils.console import TransactionProgress
from ovirt.node.utils.fs import Config
from ovirt.node.setup.rhn import rhn_model
import ovirtnode.ovirtfunctions as _functions
from ovirt.node.plugins import Changeset

RHSM_CONF = "/etc/rhsm/rhsm.conf"
SYSTEMID = "/etc/sysconfig/rhn/systemid"

args = _functions.get_cmdline_args()
keys = ["rhn_type", "rhn_url", "rhn_ca_cert", "rhn_username",
        "rhn_profile", "rhn_activationkey", "rhn_org",
        "rhn_proxy", "rhn_proxyuser"]

keys_to_model = {"rhn_type": "rhn.rhntype",
                 "rhn_url": "rhn.url",
                 "rhn_ca_cert": "rhn.ca_cert",
                 "rhn_username": "rhn.username",
                 "rhn_profile": "rhn.profile",
                 "rhn_activationkey": "rhn.activationkey",
                 "rhn_org": "rhn.org",
                 "rhn_proxy": "rhn.proxy",
                 "rhn_proxyuser": "rhn.proxyuser",
                 }

changes = dict((keys_to_model[key], args[key]) for key in keys if key in args)

if __name__ == "__main__":
    cfg = Config()
    if cfg.exists(RHSM_CONF) or cfg.exists(SYSTEMID):
        # skip rerunning again
        exit()
    rhn = rhn_model.RHN()
    cfg = rhn.retrieve()
    rhn_password = _functions.OVIRT_VARS["OVIRT_RHN_PASSWORD"] \
                   if "OVIRT_RHN_PASSWORD" in _functions.OVIRT_VARS else ""
    rhn_proxypassword = _functions.OVIRT_VARS["OVIRT_RHN_PROXYPASSWORD"] \
                        if "OVIRT_RHN_PROXYPASSWORD" in _functions.OVIRT_VARS \
                        else ""

    cfg['rhntype'] = cfg['rhntype'] or 'rhn'
    effective_model = Changeset({
        "rhn.rhntype": cfg['rhntype'],
        "rhn.url": cfg['url'],
        "rhn.ca_cert": cfg['ca_cert'],
        "rhn.username": cfg['username'],
        "rhn.profile": cfg['profile'],
        "rhn.activationkey": cfg['activationkey'],
        "rhn.org": cfg['org'],
        "rhn.proxy": cfg['proxy'],
        "rhn.proxyuser": cfg['proxyuser'],
    })
    effective_model.update(changes)
    rhn.update(*effective_model.values_for(
        [keys_to_model[key] for key in keys]))
    if cfg['username'] and rhn_password or cfg['activationkey']:
        tx = rhn.transaction(password=rhn_password, \
                             proxypass=rhn_proxypassword)
        TransactionProgress(tx, is_dry=False).run()
        # remove /etc/default/ovirt entries from being persisted
        pw_keys = ("OVIRT_RHN_PASSWORD", "OVIRT_RHN_PROXYPASSWORD")
        rhn.clear(keys=pw_keys)
