AC_INIT([ovirt-node], [1.9.1], [ovirt-devel@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign -Wno-portability tar-pax])
AC_PROG_CC
AC_CONFIG_HEADERS([config.h])

# If using gcc and default CFLAGS, enable some warnings.
test x"$ac_ct_CC:$CFLAGS" = 'xgcc:-g -O2' \
  && CFLAGS="$CFLAGS -Wshadow -Wall -Werror"

AC_CONFIG_FILES([Makefile
  images/Makefile
  kinit/Makefile
  nodeadmin/Makefile
  scripts/Makefile
  tools/Makefile
  scripts/collectd.conf
  nodeadmin/setup.py
  gptsync/Makefile
  recipe/Makefile
  ovirt-node.spec
  ])
AC_OUTPUT
