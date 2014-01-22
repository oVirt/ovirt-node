AC_INIT([ovirt-node], [3.1.0], [node-devel@ovirt.org])
AM_INIT_AUTOMAKE([-Wall -Werror foreign -Wno-portability tar-pax])

AC_SUBST([FEDORA],[[`rpm --eval '%{fedora}'|sed 's/[^0-9]//g'`]])
AC_SUBST([RHEL], [[`rpm --eval '%{rhel}'|sed 's/[^0-9]//g'`]])
AC_SUBST([CENTOS], [[`rpm --eval '%{centos}'|sed 's/[^0-9]//g'`]])
AC_SUBST([DISTRO])
AC_SUBST([PACKAGE_NAME])
AC_SUBST([PRODUCT_NAME])

if test "$FEDORA"; then
    DISTRO=ovirt$FEDORA
fi
if test "$RHEL"; then
    DISTRO=rhevh$RHEL
fi
if test "$CENTOS"; then
    DISTRO=centos$CENTOS
fi

AM_CONDITIONAL(TARGET_FEDORA, test x"$FEDORA" != x)
AM_CONDITIONAL(TARGET_RHEL, test x"$RHEL" != x && test x"$CENTOS" == x)
AM_CONDITIONAL(TARGET_CENTOS, test x"$CENTOS" != x)
AM_CONDITIONAL(TARGET_EL6, test x"$RHEL" != x || test x"$CENTOS" != x)
AM_CONDITIONAL(TARGET_SYSTEMD, test 0$RHEL -ge 7 || test 0$FEDORA -ge 16 || test 0$CENTOS -ge 7)
AM_CONDITIONAL(TARGET_NEW_DRACUT, test 0$RHEL -ge 7 || test 0$FEDORA -ge 15 || test 0$CENTOS -ge 7)
AM_CONDITIONAL(TARGET_RDLIVECHECK, test 0$RHEL -ge 7 || test 0$FEDORA -ge 15 || test 0$CENTOS -ge 7)

AM_COND_IF([TARGET_SYSTEMD],
    [SEMODULE_WITH_SYSTEMD=""], [SEMODULE_WITH_SYSTEMD="#"])
AM_COND_IF([TARGET_EL6],
    [SEMODULE_NOT_EL6="#"], [SEMODULE_NOT_EL6=""])
AC_SUBST([SEMODULE_WITH_SYSTEMD])
AC_SUBST([SEMODULE_NOT_EL6])

AM_COND_IF([TARGET_NEW_DRACUT],
     [DRACUTDIR="/usr/lib/dracut/modules.d"], [DRACUTDIR="/usr/share/dracut/modules.d"])
AC_SUBST([DRACUTDIR])

AM_COND_IF([TARGET_RDLIVECHECK],
    [BOOTLOADER_ARGS="rd.live.check rd.lvm=0"], [BOOTLOADER_ARGS="check RD_NO_LVM"])
AC_SUBST([BOOTLOADER_ARGS])

AC_ARG_WITH([image-minimizer], [AC_HELP_STRING([--with-image-minimizer],
            [enable aggresive reduction of the image size])],
            [IMAGE_MINIMIZER="%include image-minimizer.ks"],
            [IMAGE_MINIMIZER=""])
AC_SUBST([IMAGE_MINIMIZER])

AC_ARG_WITH([manifests], [AC_HELP_STRING([--without-manifests],
            [disable manifest generation at build time])],
            [MANIFESTS_INCLUDED=""],
            [MANIFESTS_INCLUDED="%include common-manifest.ks"])
AC_SUBST([MANIFESTS_INCLUDED])

AC_ARG_WITH([archipel], [AC_HELP_STRING([--with-archipel],
            [build ovirt node including Archipel])],
            [ARCHIPEL_FLAGS="--with-archipel"],
            [ARCHIPEL_FLAGS=""])
AC_SUBST([ARCHIPEL_FLAGS])


if test $ARCHIPEL_FLAGS; then
    PACKAGE_NAME=archipel-node-image
    PRODUCT_NAME=Archipel\ Node\ Hypervisor\ $DISTRO
    MAIN_KS=recipe/archipel-node-image.ks

else
    PACKAGE_NAME=ovirt-node-image
    PRODUCT_NAME=oVirt\ Node\ Hypervisor
    MAIN_KS=recipe/ovirt-node-image.ks
fi

AM_PATH_PYTHON

AC_CONFIG_FILES([Makefile
                data/Makefile
                dracut/Makefile
                images/Makefile
                scripts/Makefile
                tools/Makefile
                scripts/collectd.conf
                src/Makefile
                services/Makefile
                recipe/Makefile
                logrotate/Makefile
                modules/Makefile
                plugins/Makefile
                tests/Makefile
                $MAIN_KS
                recipe/common-install.ks
                recipe/image-minimizer.ks
                scripts/ovirt-functions
                scripts/ovirt-init-functions.sh
                semodule/ovirt.te
                ovirt-node.spec])
AC_OUTPUT
