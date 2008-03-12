%include common-install.ks

%packages
%include common-pkgs.ks
-glibc.i686
-xen-libs.i386
-libxml2.i386
-zlib.i386
-libvirt.i386
-avahi.i386
-libgcrypt.i386
-gnutls.i386
-libstdc++.i386
-e2fsprogs-libs.i386
-ncurses.i386
-readline.i386
-libselinux.i386
-device-mapper-libs.i386
-libdaemon.i386
-dbus-libs.i386
-expat.i386
-libsepol.i386
-libcap.i386
-libgpg-error.i386
-libgcc.i386
-cyrus-sasl-gssapi.i386
-cyrus-sasl-lib.i386

%post
%include common-post.ks

%end
