droprpm system-config-*
keeprpm system-config-keyboard-base

# Needed for selinux-policy generation
#droprpm mkinitrd
#droprpm checkpolicy
#droprpm make
drop /usr/share/selinux

droprpm gamin
droprpm pm-utils
droprpm usermode
droprpm vbetool
droprpm ConsoleKit
droprpm linux-atm-libs
droprpm mtools
droprpm syslinux
droprpm wireless-tools
droprpm radeontool
droprpm gnupg2
droprpm fedora-release-notes
droprpm fedora-logos

# rhbz#641494 - drop unnecessary rpms pulled in from libguestfs-winsupport
droprpm fakechroot
droprpm fakechroot-libs
droprpm fakeroot
droprpm fakeroot-libs
droprpm febootstrap

# cronie pulls in exim (sendmail) which pulls in all kinds of perl deps
droprpm exim
droprpm perl*
keeprpm perl-libs
droprpm postfix
droprpm mysql*

droprpm sysklogd
# pam complains when this is missing
keeprpm ConsoleKit-libs

drop /usr/share/zoneinfo
keep /usr/share/zoneinfo/UTC

drop /etc/alsa
drop /usr/share/alsa
drop /usr/share/awk
drop /usr/share/vim
drop /usr/share/anaconda
drop /usr/share/backgrounds
drop /usr/share/wallpapers
drop /usr/share/kde-settings
drop /usr/share/gnome-background-properties
drop /usr/share/setuptool
drop /usr/share/hwdata/MonitorsDB
drop /usr/share/hwdata/oui.txt
drop /usr/share/hwdata/videoaliases
drop /usr/share/hwdata/videodrivers
drop /usr/share/firstboot
drop /usr/share/lua
drop /usr/share/kde4
drop /usr/share/pixmaps
drop /usr/share/icons
drop /usr/share/fedora-release
drop /usr/share/tabset
drop /usr/share/tc
drop /usr/share/emacs
drop /usr/share/info
drop /usr/src
drop /usr/etc
drop /usr/games
drop /usr/include
keep /usr/include/python2.*
drop /usr/local
drop /usr/sbin/dell*
keep /usr/sbin/build-locale-archive
drop /usr/sbin/glibc_post_upgrade.*
drop /usr/lib*/tc
drop /usr/lib*/tls
drop /usr/lib*/sse2
drop /usr/lib*/pkgconfig
drop /usr/lib*/nss
drop /usr/lib*/games
drop /usr/lib*/alsa-lib
drop /usr/lib*/krb5
drop /usr/lib*/hal
drop /usr/lib*/gio
# syslinux
drop /usr/share/syslinux
# glibc-common locales
drop /usr/lib/locale
keep /usr/lib/locale/locale-archive
keep /usr/lib/locale/usr/share/locale/en_US
# pango
drop /usr/lib*/pango
drop /usr/lib*/libthai*
drop /usr/share/libthai
drop /usr/bin/pango*
# hal
drop /usr/bin/hal-disable-polling
drop /usr/bin/hal-is-caller-locked-out
drop /usr/bin/hal-is-caller-privileged
drop /usr/bin/hal-lock
drop /usr/bin/hal-set-property
drop /usr/bin/hal-setup-keymap
# openssh
drop /usr/bin/sftp
drop /usr/bin/slogin
drop /usr/bin/ssh-add
drop /usr/bin/ssh-agent
drop /usr/bin/ssh-keyscan
# docs
drop /usr/share/omf
drop /usr/share/gnome
drop /usr/share/doc
keep /usr/share/doc/libvirt*
drop /usr/share/locale/
keep /usr/share/locale/en_US
keep /usr/share/locale/zh_CN
keep /usr/share/locale/pt_BR
drop /usr/share/man
drop /usr/share/X11
drop /usr/share/i18n
drop /boot/*
keep /boot/efi
keep /boot/System.map*
keep /boot/symvers*
drop /var/lib/builder
drop /usr/sbin/*-channel

drop /usr/lib*/libboost*
keep /usr/lib*/libboost_program_options.so*
keep /usr/lib*/libboost_filesystem.so*
keep /usr/lib*/libboost_thread-mt.so*
keep /usr/lib*/libboost_thread.so*
keep /usr/lib*/libboost_system.so*
keep /usr/lib*/libboost_system-mt.so*
keep /usr/lib*/libboost_chrono-mt.so*
drop /usr/kerberos
keep /usr/kerberos/bin/kinit
keep /usr/kerberos/bin/klist

drop /etc/pki/tls
keep /etc/pki/tls/openssl.cnf
drop /etc/pki/java
drop /etc/pki/nssdb


#desktop files
drop /etc/xdg/autostart/restorecond.desktop

#ebtables depends on perl
drop /sbin/ebtables-save
drop /sbin/ebtables-restore

# remove bogus kdump script (rpmdiff complains)
drop /etc/kdump-adv-conf

#remove rpms added by dmraid
droprpm ConsoleKit
droprpm checkpolicy
droprpm dmraid-events
droprpm gamin
droprpm gnupg2
droprpm linux-atm-libs
droprpm make
droprpm mtools
droprpm mysql-libs
droprpm perl
droprpm perl-Module-Pluggable
droprpm perl-Net-Telnet
droprpm perl-PathTools
droprpm perl-Pod-Escapes
droprpm perl-Pod-Simple
droprpm perl-Scalar-List-Utils
droprpm perl-hivex
droprpm perl-macros
droprpm sgpio
droprpm syslinux
droprpm system-config-firewall-base
droprpm usermode

#NFS Server
drop /usr/bin/rpcgen
drop /usr/sbin/rpc.gssd
drop /usr/sbin/rpcdebug
