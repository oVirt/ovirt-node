#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# security.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import base, valid, utils
from ovirt.node.utils import system
from ovirt.node.utils.fs import File
import PAM as _PAM  # @UnresolvedImport
import cracklib
from collections import namedtuple
import hashlib
import os.path
import process
import selinux

"""
Some convenience functions related to security
"""


def password_check(password, confirmation, min_length=1):
    '''
    Do some password checks
    Returns:
        A message about a possibly weak password

    >>> password_check("", "", min_length=0) is None
    True

    >>> password_check("", "")
    Traceback (most recent call last):
    ValueError: Password must be at least 1 characters

    >>> msg = password_check("foo", "foo")
    >>> "You have provided a weak password" in msg
    True

    >>> password_check("foo", "foo", 5)
    Traceback (most recent call last):
    ValueError: Password must be at least 5 characters

    >>> password_check("foo", "bar")
    Traceback (most recent call last):
    ValueError: Passwords Do Not Match

    >>> password_check("foo", "")
    Traceback (most recent call last):
    ValueError: Please Check Password Confirmation

    >>> password_check("", "foo", 0)
    Traceback (most recent call last):
    ValueError: Please Check Password
    '''
    message = None

    if len(password) is 0 and len(confirmation) is 0 and min_length is 0:
        pass
    elif len(password) < min_length:
        raise ValueError("Password must be at least %d characters" %
                         min_length)
    elif password != "" and confirmation == "":
        raise ValueError("Please Check Password Confirmation")
    elif password == "" and confirmation != "":
        raise ValueError("Please Check Password")
    elif password != confirmation:
        raise ValueError("Passwords Do Not Match")
    else:
        try:
            cracklib.FascistCheck(password)
        except ValueError as e:
            message = "You have provided a weak password! "
            message += "Strong passwords contain a mix of uppercase, "
            message += "lowercase, numeric and punctuation characters. "
            message += "They are six or more characters long and "
            message += "do not contain dictionary words. "
            message += "Reason: %s" % e

    return message


class Passwd(base.Base):
    def set_password(self, username, password):
        import ovirtnode.password as opasswd
        opasswd.set_password(password, username)


class Selinux(base.Base):
    def restorecon(self, abspath):
        try:
            selinux.restorecon(abspath.encode("utf-8"))
        except OSError:
            self._logger.warning('No default label: "%s"', abspath)

    def getcon(self, abspath):
        """ Return context of file, symlink or dir """
        try:
            return selinux.getfilecon(abspath)[1]
        except OSError:
            self._logger.warning('Cannot get selinux context: "%s"', abspath)

    def chcon(self, abspath, context):
        """ Change selinux security context """
        try:
            return selinux.chcon(abspath, context)
        except OSError:
            self._logger.warning('Cannot change selinux context: "%s" "%s"',
                                 (abspath, context))


class Ssh(base.Base):
    def __init__(self):
        super(Ssh, self).__init__()

    def __update_profile(self, rng_num_bytes=None, disable_aes=False):
        additional_lines = []

        utils.fs.Config().unpersist("/etc/profile")

        process.check_call("sed -ic '/OPENSSL_DISABLE_AES_NI/d' /etc/profile",
                           shell=True)
        if disable_aes:
            additional_lines += ["export OPENSSL_DISABLE_AES_NI=1"]

        process.check_call("sed -ic '/SSH_USE_STRONG_RNG/d' /etc/profile",
                           shell=True)
        if rng_num_bytes:
            additional_lines += ["export SSH_USE_STRONG_RNG=%s" %
                                 rng_num_bytes]

        if additional_lines:
            self.logger.debug("Updating /etc/profile")
            lines = "\n" + "\n".join(additional_lines)
            File("/etc/profile").write(lines, "a")
            utils.fs.Config().persist("/etc/profile")

            self.restart()

    def disable_aesni(self, disable=None):
        """Set/Get AES NI for OpenSSL
        Args:
            enable: True or False
        Returns:
            The status of aes_ni
        """
        if disable in [True, False]:
            self.__update_profile(disable_aes=disable)
        else:
            self.logger.warning("Unknown value for AES NI: %s" % disable)
        return self.rng_status().disable_aes_ni

    def strong_rng(self, num_bytes=None):
        if (valid.Empty() | valid.Number(bounds=[0, None])).\
           validate(num_bytes):
            self.__update_profile(num_bytes)
        elif num_bytes is None:
            pass
        else:
            self.logger.warning("Unknown value for RNG num bytes: " +
                                "%s" % num_bytes)
        return self.rng_status().rng_bytes

    def rng_status(self):
        rng_bytes = None
        disable_aes_ni = False

        status = namedtuple("rngstatus", ["rng_bytes", "disable_aes_ni"])

        f = File("/etc/profile")
        if f.findall(r'SSH_USE_STRONG_RNG=\d+'):
            rng_bytes = f.findall(r'SSH_USE_STRONG_RNG=\d+'
                                  )[0].split('=')[1]
        if f.findall(r'DISABLE_AES_NI='):
            disable_aes_ni = True

        rng_status = status(rng_bytes, disable_aes_ni)
        return rng_status

    def restart(self):
        self.logger.debug("Restarting SSH")
        system.service("sshd", "restart")

    def password_authentication(self, enable=None):
        """Get or set the ssh password authentication

        Args:
            enable: (optional) If given the auth is set
        Returns:
            True if password authentication is enabled, False otherwise
        """
        augpath = "/files/etc/ssh/sshd_config/PasswordAuthentication"
        aug = utils.AugeasWrapper()
        if enable in [True, False]:
            value = "yes" if enable else "no"
            self.logger.debug("Setting SSH PasswordAuthentication to " +
                              "%s" % value)
            aug.set(augpath, value)
            utils.fs.Config().persist("/etc/ssh/sshd_config")
            self.restart()
        state = str(aug.get(augpath)).lower()
        if state not in ["yes", "no", "none"]:
            raise RuntimeError("Failed to set SSH password authentication" +
                               "(%s)" % state)
        return state == "yes"

    def port(self, port=None):
        augpath = "/files/etc/ssh/sshd_config/Port"
        aug = utils.AugeasWrapper()

        if port is not None and not isinstance(port, int):
            try:
                int(port)
            except ValueError:
                raise RuntimeError("Port must be an integer")
        if port is not None:
            if int(port) in range(1024, 65536) or int(port) == 22:
                self.logger.debug("Setting SSH port to %s" % port)
                aug.set(augpath, port)
                self.restart()

            else:
                raise RuntimeError("Port must be in the range [1024-65536] \
                                   or 22")

        state = str(aug.get(augpath)).lower()
        if state != "none":
            if int(state) in range(1024, 65536) or int(state) == 22:
                self.logger.debug("SSH port %s" % state)
        else:
            raise RuntimeError("Failed to set SSH port: value is %s" % state)
        return state

    def get_hostkey(self, variant="rsa"):
        fn_hostkey = "/etc/ssh/ssh_host_%s_key.pub" % variant
        if not os.path.exists(fn_hostkey):
            raise Exception("SSH hostkey does not yet exist.")

        hostkey = File(fn_hostkey).read()

        hostkey_fp_cmd = "ssh-keygen -l -f '%s'" % fn_hostkey
        out = process.pipe(hostkey_fp_cmd, shell=True)
        fingerprint = out.strip().split(" ")[1]
        return (fingerprint, hostkey)


class PAM(base.Base):
    def authenticate(self, username, password):
        is_authenticated = False
        auth = _PAM.pam()
        auth.start("passwd")
        auth.set_item(_PAM.PAM_USER, username)
        self._password = str(password)  # FIXME Bug in binding
        auth.set_item(_PAM.PAM_CONV, lambda a, q: self._pam_conv(a, q))
        try:
            auth.authenticate()
            is_authenticated = True
        except _PAM.error, (resp, code):
            self.logger.debug("Failed to authenticate: %s %s" % (resp, code))
        except Exception as e:
            self.logger.debug("Internal error: %s" % e)
        return is_authenticated

    def _pam_conv(self, auth, query_list):
        resp = []
        for i in range(len(query_list)):
            resp.append((self._password, 0))
        return resp


def checksum(data, algo="sha256"):
    """Determin the hash of some data chunk

    >>> checksum("bar", "sha256")
    'fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9'
    """
    assert algo in ["sha256", "sha512"], "Unsupported algorithm: %s" % algo

    hasher = {"sha256": hashlib.sha256,
              "sha512": hashlib.sha512}[algo]()
    hasher.update(data)
    return hasher.hexdigest()
