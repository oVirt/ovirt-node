# note: the version number here is overridden by the one in release.mk
AC_INIT([ovirt-node], [0.1], [ovirt-devel@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign])
AC_PROG_CC
AC_CONFIG_HEADERS([config.h])

# for ovirt-identify-node
PKG_CHECK_MODULES([DBUS], [dbus-1 >= 1.2.1])
PKG_CHECK_MODULES([HAL], [hal >= 0.5.11])
PKG_CHECK_MODULES([VIRT], [libvirt >= 0.4.4])

AC_CONFIG_FILES([Makefile ovirt-identify-node/Makefile])
AC_OUTPUT
