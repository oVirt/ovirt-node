#!/usr/bin/env python
#
# ovirt-upgrade-tool - Copyright (C) 2013 Red Hat, Inc.
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

import os
import sys
import shutil
import glob
import tempfile
import subprocess
import logging
import logging.handlers
import optparse
import time
import imp

LOG_PREFIX = "ovirt-node-upgrade"
OVIRT_UPGRADE_LOCK = "/tmp/.ovirt_upgrade.lock"
OVIRT_UPGRADED = "/tmp/ovirt_upgraded"

def which(file):
    ret = None
    if os.path.isabs(file) and os.path.exists(file):
        ret = file
    else:
        for dir in os.environ["PATH"].split(":"):
            f = os.path.join(dir, file)
            if os.path.exists(f) and os.access(f, os.X_OK):
                ret = f
                break
    if ret is None:
        raise RuntimeError("Cannot find command '%s'" % file)
    return ret


def initLogger():
    logger = logging.getLogger(LOG_PREFIX)
    log_file = "/var/log/ovirt-node-upgrade.log"
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)-8s - '
                                  '%(module)s - %(message)s')
    conformatter = logging.Formatter('%(name)-12s: %(levelname)-8s'
                                     ' %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(conformatter)
    logger.addHandler(console)


class Base(object):
    def __init__(self):
        self._logger = logging.getLogger(
            '%s.%s' % (LOG_PREFIX, self.__class__.__name__))


class LockFile(Base):

    def __init__(self):
        super(LockFile, self).__init__()
        self._locked = False
        lock_fd, self._lock_file = tempfile.mkstemp(prefix=".ovirtupgrade.")
        os.close(lock_fd)

    def __enter__(self):
        self._acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self._remove()

    def _acquire(self):
        self._logger.info("Acquiring Lock")
        if os.path.exists(OVIRT_UPGRADE_LOCK):
            with open(self._lock_file, "r") as f:
                if os.path.exists("/proc/%s" % f.readline()):
                    raise RuntimeError("You already have an instance of th " +
                                       " program running")
            os.remove(OVIRT_UPGRADE_LOCK)
        try:
            with open(self._lock_file, "w") as f:
                f.write("%s" % os.getpid())
            os.symlink(self._lock_file, OVIRT_UPGRADE_LOCK)
            self._locked = True
        except Exception as e:
            self._logger.exception('Error: Upgrade Failed: %s', e)
            raise RuntimeError("Unable to write lockfile")

    def _remove(self):
        try:
            if self._locked:
                os.remove(OVIRT_UPGRADE_LOCK)
            if os.path.exists(self._lock_file):
                os.remove(self._lock_file)
        except Exception as e:
            self._logger.exception('Error: Upgrade Failed: %s', e)
            raise RuntimeError("Unable to remove lockfile")


class UpgradeTool(Base):
    def __init__(self):
        super(UpgradeTool, self).__init__()
        self._options = None
        self._python_lib = None
        self._tmp_python_path = None
        self.iso_tmp = None
        self._tmp_dir = tempfile.mkdtemp(dir="/data")
        self._chroot_path = os.path.join(self._tmp_dir, "rootfs")
        self._squashfs_dir = os.path.join(self._tmp_dir, "squashfs")
        self._ovirtnode_dir = os.path.join(self._tmp_dir, "ovirtnode")
        self._ext_image = os.path.join(
            self._squashfs_dir,
            "LiveOS",
            "ext3fs.img",
        )
        self._hooks_path = "usr/libexec/ovirt-node/hooks/"
        self._logger.info("Temporary Directory is: %s", self._tmp_dir)

    def _system(self, *command):
        self._logger.debug(command)
        system_cmd = subprocess.Popen(command, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, err = system_cmd.communicate()
        output = output.decode('utf-8', 'replace').splitlines()
        self._logger.debug(output)
        self._logger.debug(err)
        if system_cmd.returncode != 0:
            raise RuntimeError("Command Failed: '%s' %s" % (command, output))

    def _parse_options(self):
        parser = optparse.OptionParser()

        parser.add_option("--reboot", type="int", default="0", dest="reboot",
                          help="Perform reboot after upgrade, argument is"
                          " amount of delay in seconds")
        parser.add_option("--skip-existing-hooks", action="store_true",
                          dest="skip_existing_hooks", default="False",
                          help="Use only new hooks from provided iso")

        parser.add_option("--iso", type="string", dest="iso_file",
                          metavar="FILE", help="Image to use for upgrade, use"
                          " - to read from stdin")
        (self._options, args) = parser.parse_args()

    def _run_hooks(self, stage):
        """Runs hooks located under a predefined location

        Args:
            stage: The hook directory name in the new or old image under
            /usr/libexec/ovirt-node/hooks/

        If existing hooks are not used only those located in the new image
        are ran. The new image is mounted to self._chroot_path
        >>> stage = "pre-upgrade"
        >>> self._chroot_path = "/data/tmp3dgfcW/rootfs"
        >>> hooks_path = os.path.join(self._hooks_path, stage)
        >>> hooks_path
        '/data/tmp3dgfcW/rootfs/usr/libexec/ovirt-node/hooks/pre-upgrade'
        """

        hooks_path = []
        if not self._options.skip_existing_hooks:
            hooks_path.append(os.path.join("/", self._hooks_path, stage))

        hooks_path.append(os.path.join(
            self._chroot_path,
            self._hooks_path,
            stage,
        ))

        for path in hooks_path:
            if not os.path.exists(path):
                self._logger.info("Warning: {path} does not exist".format
                                 (path=path))
            else:
                self._logger.info("Running {stage} hooks".format(stage=stage))
                for i in sorted(os.listdir(path)):
                    hook = os.path.join(path, i)
                    self._logger.info("Running: {hook}".format(hook=i))
                    self._system(hook)
                self._logger.info(
                    "{stage} hooks completed".format(stage=stage))

    def _extract_rootfs(self, iso):
        self._system("mount", "-o", "loop", iso, "/live")
        squashfs_dir = os.path.join(self._tmp_dir, "squashfs")
        os.mkdir(squashfs_dir)
        self._system("mount", "-o", "loop", "/live/LiveOS/squashfs.img",
                     squashfs_dir)
        os.mkdir(self._chroot_path)
        self._system(
            "mount",
            "-o", "loop",
            self._ext_image,
            self._chroot_path
        )

    def _run_upgrade(self):
        self._logger.info("hooks: %s" % self._options.skip_existing_hooks)
        self._python_lib = glob.glob("%s/rootfs/usr/lib/python*"
                                     % self._tmp_dir)
        if not self._python_lib:
            raise RuntimeError("Unable to determine python path")
        self._python_lib = self._python_lib[0]
        sys.path.append(self._python_lib + "/site-packages/")
        self._tmp_python_path = "%s/site-packages/ovirtnode" \
            % self._python_lib
        shutil.copytree(self._tmp_python_path, self._ovirtnode_dir)
        # import install and ovirtfunctions modules from new image
        f, filename, description = imp.find_module(
            'install',
            [self._ovirtnode_dir],
        )
        install = imp.load_module(
            'install',
            f,
            filename,
            description,
        )
        f, filename, description = imp.find_module(
            'ovirtfunctions',
            [self._ovirtnode_dir],
        )
        ovirtfunctions = imp.load_module(
            'ovirtfunctions',
            f,
            filename,
            description,
        )
        # log module detail for debugging
        self._logger.debug(install)
        import install
        import ovirtfunctions as _functions_new
        install._functions = _functions_new
        upgrade = install.Install()
        self._logger.propagate = True
        self._logger.info("Installing Bootloader")
        if not upgrade.ovirt_boot_setup():
            raise RuntimeError("Bootloader Installation Failed")

        sys.path.append(self._python_lib + "/site-packages/")
        from ovirt.node.config import migrate
        migrate.MigrateConfigs().translate_all()

    def _cleanup(self):
        self._logger.info("Cleaning up temporary directory")
        try:
            for dir in [self._chroot_path, self._squashfs_dir, "/live"]:
                self._system(which("umount"), dir)
            shutil.rmtree(self._tmp_dir)
            if self.iso_tmp and os.path.exists(self.iso_tmp):
                os.remove(self.iso_tmp)
            open(OVIRT_UPGRADED, 'w').close()
            # check is iscsi install
            if os.path.exists("/boot/ovirt"):
                # prevent network from shutting down and
                # killing rootfs for live upgrades
                os.remove("/var/lock/subsys/network")
        except:
            self._logger.warning("Cleanup Failed")
            self._logger.debug('exception', exc_info=True)

    def _simpleDaemon(self, main, args=(), kwargs={}):
        # Default maximum for the number of available file descriptors.
        MAXFD = 1024

        import resource  # Resource usage information.
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if (maxfd == resource.RLIM_INFINITY):
            maxfd = MAXFD

        pid = os.fork()
        if pid == 0:
            try:
                os.chdir('/')
                os.setsid()
                for fd in range(0, maxfd):
                    try:
                        os.close(fd)
                    except OSError:
                        # ERROR, fd wasn't open to begin with (ignored)
                        pass

                os.open(os.devnull, os.O_RDWR)  # standard input (0)
                os.dup2(0, 1)  # standard output (1)
                os.dup2(0, 2)  # standard error (2)

                if os.fork() != 0:
                    os._exit(0)

                try:
                    main(*args, **kwargs)
                except:
                    import traceback
                    traceback.print_exc()
            finally:
                os._exit(1)

        pid, status = os.waitpid(pid, 0)

        if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
            raise RuntimeError('Daemon not exited properly')

    def _delayedReboot(self, reboot, sleepTime):
        time.sleep(sleepTime)
        os.execl(reboot, reboot)

    def _reboot(self, delay):
        self._logger.info("Scheduling Reboot")
        self._simpleDaemon(
            self._delayedReboot,
            (
                which("reboot"),
                delay,
            )
        )
        self._logger.info("Reboot Scheduled")

    def run(self):
        self._parse_options()
        self._logger.debug(self._options)
        if os.geteuid() != 0:
            raise RuntimeError("You must run as root")
        if os.path.exists(OVIRT_UPGRADED):
            raise RuntimeError("Previous upgrade completed, you must reboot")

        with LockFile():
            if not self._options.iso_file:
                raise RuntimeError("iso file not defined")
            elif self._options.iso_file == "-":
                iso_fd, self._options.iso_file = tempfile.mkstemp(
                    dir="/data",
                    prefix="tmpiso_",
                )
                self.iso_tmp = self._options.iso_file
                os.close(iso_fd)
                self._logger.debug("Using temporary ISO file: {iso}\n".format
                                  (iso=self._options.iso_file))
                with open(self._options.iso_file, 'wb') as f:
                    while True:
                        data = sys.stdin.read(4096)
                        if not data:
                            break
                        f.write(data)
            elif not os.path.exists(self._options.iso_file):
                raise RuntimeError("%s does not exist" %
                                   self._options.iso_file)
            try:
                self._extract_rootfs(self._options.iso_file)
                self._run_hooks("pre-upgrade")
                self._run_upgrade()
                self._run_hooks("post-upgrade")
                if self._options.reboot > 0:
                    self._reboot(self._options.reboot)
                self._logger.info("Upgrade Completed")
            except Exception as e:
                self._logger.exception('Error: Upgrade Failed: %s', e)
                self._run_hooks("rollback")
                self._logger.info("Upgrade Failed, Rollback Completed")
                ret = 1
            finally:
                self._cleanup()
                ret = 0
            sys.exit(ret)

if __name__ == "__main__":
    initLogger()
    u = UpgradeTool()
    u.run()
