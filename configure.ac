AC_INIT([ovirt-node], [1.9.3], [ovirt-devel@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign -Wno-portability tar-pax])
AC_PROG_CC

AC_CHECK_PROGS(PYKICKSTART, ksflatten)

if test x"$PYKICKSTART" = x ; then
   AC_MSG_ERROR([Missing python kickstart support.])
fi

# TODO need a way to check for python-setuptools

AC_CHECK_LIB(virt, main, , AC_MSG_ERROR([Cannot find libvirt development libraries.]))
AC_CHECK_LIB(python2.7, main, , AC_MSG_ERROR([Cannot find python development libraries.]))

AC_CONFIG_HEADERS([config.h])

# If using gcc and default CFLAGS, enable some warnings.
test x"$ac_ct_CC:$CFLAGS" = 'xgcc:-g -O2' \
  && CFLAGS="$CFLAGS -Wshadow -Wall -Werror"

AC_CONFIG_FILES([Makefile
  dracut/Makefile
  images/Makefile
  kinit/Makefile
  scripts/Makefile
  tools/Makefile
  scripts/collectd.conf
  gptsync/Makefile
  recipe/Makefile
  ovirt-node.spec
  ])
AC_OUTPUT
