AC_INIT([ovirt-node], [1.0.3], [ovirt-devel@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign -Wno-portability tar-pax])
AC_PROG_CC
AC_CONFIG_HEADERS([config.h])

# If using gcc and default CFLAGS, enable some warnings.
test x"$ac_ct_CC:$CFLAGS" = 'xgcc:-g -O2' \
  && CFLAGS="$CFLAGS -Wshadow -Wall -Werror"

AC_CONFIG_FILES([Makefile
  gptsync/Makefile
  ovirt-node.spec
  ])
AC_OUTPUT
