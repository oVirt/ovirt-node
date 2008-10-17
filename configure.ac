AC_INIT([ovirt-node], [0.94.2], [ovirt-devel@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign -Wno-portability tar-pax])
AC_PROG_CC
AC_CONFIG_HEADERS([config.h])

# for ovirt-identify-node
PKG_CHECK_MODULES([DBUS], [dbus-1 >= 1.0.0])
PKG_CHECK_MODULES([HAL], [hal >= 0.5.8])
PKG_CHECK_MODULES([VIRT], [libvirt >= 0.4.4])

# If using gcc and default CFLAGS, enable some warnings.
test x"$ac_ct_CC:$CFLAGS" = 'xgcc:-g -O2' \
  && CFLAGS="$CFLAGS -Wshadow -Wall -Werror"

AC_CONFIG_FILES([Makefile
  ovirt-identify-node/Makefile
  ovirt-listen-awake/Makefile
  ovirt-node.spec
  ])
AC_OUTPUT
