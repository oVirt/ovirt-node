droprpm system-config-*
keeprpm system-config-keyboard-base

# Needed for selinux-policy generation
#droprpm mkinitrd
#droprpm checkpolicy
#droprpm make
drop /usr/share/selinux
droprpm selinux-policy-devel

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

# kernel modules minimization

# filesystems
drop /lib/modules/*/kernel/fs
keep /lib/modules/*/kernel/fs/ext*
keep /lib/modules/*/kernel/fs/mbcache*
keep /lib/modules/*/kernel/fs/squashfs
keep /lib/modules/*/kernel/fs/jbd*
keep /lib/modules/*/kernel/fs/btrfs
keep /lib/modules/*/kernel/fs/cifs*
keep /lib/modules/*/kernel/fs/fat
keep /lib/modules/*/kernel/fs/nfs
keep /lib/modules/*/kernel/fs/nfsd
keep /lib/modules/*/kernel/fs/nfs_common
keep /lib/modules/*/kernel/fs/fscache
keep /lib/modules/*/kernel/fs/lockd
keep /lib/modules/*/kernel/fs/nls/nls_utf8.ko
keep /lib/modules/*/kernel/fs/configfs/configfs.ko
keep /lib/modules/*/kernel/fs/fuse
keep /lib/modules/*/kernel/fs/isofs
# autofs4     configfs  exportfs *fat     *jbd    mbcache.ko  nls       xfs
#*btrfs       cramfs   *ext2     *fscache *jbd2  *nfs         squashfs
# cachefiles  dlm      *ext3      fuse     jffs2 *nfs_common  ubifs
# cifs        ecryptfs *ext4      gfs2    *lockd  nfsd        udf

# network
drop /lib/modules/*/kernel/net
keep /lib/modules/*/kernel/net/802*
keep /lib/modules/*/kernel/net/bridge
keep /lib/modules/*/kernel/net/core
keep /lib/modules/*/kernel/net/dns_resolver
keep /lib/modules/*/kernel/net/ipv*
keep /lib/modules/*/kernel/net/key
keep /lib/modules/*/kernel/net/llc
keep /lib/modules/*/kernel/net/netfilter
keep /lib/modules/*/kernel/net/rds
keep /lib/modules/*/kernel/net/sctp
keep /lib/modules/*/kernel/net/sched
keep /lib/modules/*/kernel/net/sunrpc
#*802    atm        can   ieee802154 *key      *netfilter  rfkill *sunrpc  xfrm
#*8021q  bluetooth *core *ipv4       *llc       phonet     sched   wimax
# 9p    *bridge     dccp *ipv6        mac80211 *rds       *sctp    wireless

drop /lib/modules/*/kernel/sound

# drivers
drop /lib/modules/*/kernel/drivers
keep /lib/modules/*/kernel/drivers/ata
keep /lib/modules/*/kernel/drivers/block
keep /lib/modules/*/kernel/drivers/cdrom
keep /lib/modules/*/kernel/drivers/char
keep /lib/modules/*/kernel/drivers/cpufreq
keep /lib/modules/*/kernel/drivers/dca
keep /lib/modules/*/kernel/drivers/dma
keep /lib/modules/*/kernel/drivers/edac
keep /lib/modules/*/kernel/drivers/firmware
keep /lib/modules/*/kernel/drivers/idle
keep /lib/modules/*/kernel/drivers/infiniband
keep /lib/modules/*/kernel/drivers/input/misc/uinput.ko
keep /lib/modules/*/kernel/drivers/md
keep /lib/modules/*/kernel/drivers/message
keep /lib/modules/*/kernel/drivers/net
drop /lib/modules/*/kernel/drivers/net/pcmcia
drop /lib/modules/*/kernel/drivers/net/wireless
drop /lib/modules/*/kernel/drivers/net/ppp*
keep /lib/modules/*/kernel/drivers/pci
keep /lib/modules/*/kernel/drivers/pps
keep /lib/modules/*/kernel/drivers/ptp
keep /lib/modules/*/kernel/drivers/scsi
keep /lib/modules/*/kernel/drivers/staging/ramzswap
keep /lib/modules/*/kernel/drivers/uio
keep /lib/modules/*/kernel/drivers/usb
drop /lib/modules/*/kernel/drivers/usb/atm
drop /lib/modules/*/kernel/drivers/usb/class
drop /lib/modules/*/kernel/drivers/usb/image
drop /lib/modules/*/kernel/drivers/usb/misc
drop /lib/modules/*/kernel/drivers/usb/serial
keep /lib/modules/*/kernel/drivers/usb/storage
keep /lib/modules/*/kernel/drivers/vhost
keep /lib/modules/*/kernel/drivers/virtio
keep /lib/modules/*/kernel/drivers/watchdog
keep /lib/modules/*/kernel/drivers/i2c

# acpi       *cpufreq   hid         leds      mtd      ?regulator  uwb
#*ata         crypto   ?hwmon      *md       *net*      rtc       *vhost
# atm        *dca      ?i2c         media    ?parport  *scsi*      video
# auxdisplay *dma      *idle        memstick *pci      ?serial    *virtio
#*block      *edac      ieee802154 *message   pcmcia   ?ssb        watchdog
# bluetooth   firewire *infiniband ?mfd       platform *staging    xen
#*cdrom      *firmware  input       misc     ?power    ?uio
#*char*      ?gpu       isdn        mmc      ?pps      *usb

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
drop /usr/share/augeas/lenses/tests
drop /usr/share/augeas/lenses/dist/*
# generic includes
keep /usr/share/augeas/lenses/dist/build.aug
keep /usr/share/augeas/lenses/dist/hosts.aug
keep /usr/share/augeas/lenses/dist/inifile.aug
keep /usr/share/augeas/lenses/dist/modprobe.aug
keep /usr/share/augeas/lenses/dist/rx.aug
keep /usr/share/augeas/lenses/dist/sep.aug
keep /usr/share/augeas/lenses/dist/shellvars.aug
keep /usr/share/augeas/lenses/dist/spacevars.aug
keep /usr/share/augeas/lenses/dist/sysctl.aug
keep /usr/share/augeas/lenses/dist/util.aug
keep /usr/share/augeas/lenses/dist/simplevars.aug
# whitelist only relevant lenses
keep /usr/share/augeas/lenses/dist/buildd.aug
keep /usr/share/augeas/lenses/dist/cgconfig.aug
keep /usr/share/augeas/lenses/dist/cgrules.aug
keep /usr/share/augeas/lenses/dist/cron.aug
keep /usr/share/augeas/lenses/dist/dhclient.aug
keep /usr/share/augeas/lenses/dist/dnsmasq.aug
keep /usr/share/augeas/lenses/dist/ethers.aug
keep /usr/share/augeas/lenses/dist/exports.aug
keep /usr/share/augeas/lenses/dist/fstab.aug
keep /usr/share/augeas/lenses/dist/group.aug
keep /usr/share/augeas/lenses/dist/grub.aug
keep /usr/share/augeas/lenses/dist/inittab.aug
keep /usr/share/augeas/lenses/dist/iptables.aug
keep /usr/share/augeas/lenses/dist/json.aug
keep /usr/share/augeas/lenses/dist/krb5.aug
keep /usr/share/augeas/lenses/dist/kdump.aug
keep /usr/share/augeas/lenses/dist/limits.aug
keep /usr/share/augeas/lenses/dist/logrotate.aug
keep /usr/share/augeas/lenses/dist/lokkit.aug
keep /usr/share/augeas/lenses/dist/modules_conf.aug
keep /usr/share/augeas/lenses/dist/multipath.aug
keep /usr/share/augeas/lenses/dist/ntp.aug
keep /usr/share/augeas/lenses/dist/pam.aug
keep /usr/share/augeas/lenses/dist/passwd.aug
keep /usr/share/augeas/lenses/dist/quote.aug
keep /usr/share/augeas/lenses/dist/resolv.aug
keep /usr/share/augeas/lenses/dist/rsyslog.aug
keep /usr/share/augeas/lenses/dist/securetty.aug
keep /usr/share/augeas/lenses/dist/services.aug
keep /usr/share/augeas/lenses/dist/shellvars_list.aug
keep /usr/share/augeas/lenses/dist/sshd.aug
keep /usr/share/augeas/lenses/dist/sudoers.aug
keep /usr/share/augeas/lenses/dist/syslog.aug
keep /usr/share/augeas/lenses/dist/utill.aug
keep /usr/share/augeas/lenses/dist/yum.aug
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
drop /lib/firmware
keep /lib/firmware/3com
keep /lib/firmware/acenic
keep /lib/firmware/adaptec
keep /lib/firmware/advansys
keep /lib/firmware/bnx2
keep /lib/firmware/bnx2x
keep /lib/firmware/bnx2x*
keep /lib/firmware/cxgb3
keep /lib/firmware/cxgb4
keep /lib/firmware/e100
keep /lib/firmware/myricom
keep /lib/firmware/ql*
keep /lib/firmware/sun
keep /lib/firmware/tehuti
keep /lib/firmware/tigon
keep /lib/firmware/cbfw*
keep /lib/firmware/ctfw*
keep /lib/firmware/ct2fw*
keep /lib/firmware/aic94xx-seq.fw

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
