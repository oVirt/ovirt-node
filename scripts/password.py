#!/usr/bin/python
# password.py - Copyright (C) 2010 Red Hat, Inc.
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

from ovirtnode.ovirtfunctions import *
import libuser
import random
import crypt

def cryptPassword(password):
    saltlen = 2
    algo = 'sha512'
    saltlen = 16
    saltstr = '$6$'
    for i in range(saltlen):
        saltstr = saltstr + random.choice (string.letters +
                                           string.digits + './')
    return crypt.crypt (password, saltstr)

def set_password(password, user):
    admin = libuser.admin()
    root = admin.lookupUserByName(user)
    passwd = cryptPassword(password)
    admin.setpassUser(root, passwd, "is_crypted")
    unmount_config("/etc/shadow")
    ovirt_store_config("/etc/shadow")
    return True

def check_ssh_password_auth():
    password_auth_status = augeas.Augeas("root=/")
    password_auth_status.get("/files/etc/ssh/sshd_config/PasswordAuthentication")
    return password_auth_status

def toggle_ssh_access():
    ssh_config = augeas.Augeas("root=/")
    ssh_config.set("/files/etc/ssh/sshd_config", OVIRT_VARS["ssh_pass_enabled"])
    ssh_config.save()
    ovirt_store_config("/etc/ssh/sshd_config")
    rc = os.system("service sshd reload")
    return rc

def set_sasl_password(user, password):
    os.system("saslpasswd2 -a libvirt -p %s") % user
