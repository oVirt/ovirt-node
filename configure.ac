AC_INIT([ovirt-node], [2.3.0], [node-devel@ovirt.org])
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


AC_CONFIG_FILES([Makefile
                dracut/Makefile
                images/Makefile
                kinit/Makefile
                scripts/Makefile
                tools/Makefile
                scripts/collectd.conf
                recipe/Makefile
                $MAIN_KS
                recipe/image-minimizer.ks
                ovirt-node.spec])
AC_OUTPUT
