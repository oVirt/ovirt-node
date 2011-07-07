AC_INIT([ovirt-node], [2.0.1], [ovirt-devel@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign -Wno-portability tar-pax])
AC_PROG_CC

AC_SUBST([FEDORA],[[`rpm --eval '%{fedora}'|sed 's/[^0-9]//g'`]])
AC_SUBST([RHEL], [[`rpm --eval '%{rhel}'|sed 's/[^0-9]//g'`]])
AC_SUBST([DISTRO])

if test "$FEDORA"; then
    DISTRO=ovirt$FEDORA
fi
if test "$RHEL"; then
    DISTRO=rhevh$RHEL
fi

AC_CONFIG_HEADERS([config.h])

# If using gcc and default CFLAGS, enable some warnings.
test x"$ac_ct_CC:$CFLAGS" = 'xgcc:-g -O2' \
  && CFLAGS="$CFLAGS -Wshadow -Wall -Werror"

AC_CONFIG_FILES([Makefile
  augeas/Makefile
  dracut/Makefile
  images/Makefile
  kinit/Makefile
  scripts/Makefile
  scripts/collectd.conf
  recipe/Makefile
  recipe/ovirt-node-image.ks
  ovirt-node.spec
  ])
AC_OUTPUT
