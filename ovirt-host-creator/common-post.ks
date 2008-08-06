# -*-Shell-script-*-
echo "Starting Kickstart Post"
PATH=/sbin:/usr/sbin:/bin:/usr/bin
export PATH

echo "Creating shadow files"
# because we aren't installing authconfig, we aren't setting up shadow
# and gshadow properly.  Do it by hand here
pwconv
grpconv

echo "Forcing C locale"
# force logins (via ssh, etc) to use C locale, since we remove locales
cat >> /etc/profile << \EOF
# oVirt: force our locale to C since we don't have locale stuff'
export LC_ALL=C LANG=C
EOF

echo "Configuring IPTables"
# here, we need to punch the appropriate holes in the firewall
cat > /etc/sysconfig/iptables << \EOF
# oVirt automatically generated firewall configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -p tcp --dport 16509 -j ACCEPT
-A INPUT -p tcp --dport 22 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOF

echo "Removing excess RPMs"

# kernel pulls in mkinitrd which pulls in isomd5sum which pulls in python,
# and livecd-tools needs lokkit to disable SELinux.
# However, this is just an install-time dependency; we can remove
# it afterwards, which we do here
rpm -e system-config-firewall-tui system-config-network-tui rhpl \
    rpm-python dbus-python kudzu newt-python newt
rpm -e qemu kpartx mkinitrd isomd5sum dmraid python python-libs

RPM="rpm -v -e --nodeps"

# Sigh.  ntp has a silly dependency on perl because of auxiliary scripts which
# we don't need to use.  Forcibly remove it here
$RPM perl perl-libs perl-Module-Pluggable perl-version \
    perl-Pod-Simple perl-Pod-Escapes

# Remove additional RPMs forcefully
$RPM gamin pm-utils kbd libuser passwd usermode \
    vbetool ConsoleKit hdparm \
    efibootmgr krb5-workstation linux-atm-libs fedora-release-notes \
    slang psmisc gdbm cryptsetup-luks pciutils mtools syslinux db4 \
    wireless-tools radeontool cracklib-dicts cracklib

# Things we could probably remove if libvirt didn't link against them
#$RPM avahi PolicyKit xen-libs

# Things we could probably remove if qemu-kvm didn't link against them
#$RPM SDL alsa-lib

# Pam complains when this is missing
#$RPM ConsoleKit-libs

RM="rm -rf"

echo "Removing excess kernel modules"
MODULES="/lib/modules/*/kernel"

# the following are lists of kernel modules we are pretty sure we won't need;
# note that these can be single files or whole directories.  They are specified
# starting at $MODULES above; so if you want to remove the NLS stuff from the
# fs subdir, your mods entry would be "fs/nls"
fs_mods="fs/nls fs/9p fs/affs fs/autofs fs/autofs4 fs/befs fs/bfs fs/cifs \
       fs/coda fs/cramfs fs/dlm fs/ecryptfs fs/efs fs/exportfs fs/ext4 \
       fs/freevxfs fs/fuse fs/gfs2 fs/hfs fs/hfsplus fs/jbd fs/jbd2 fs/jffs \
       fs/jffs2 fs/jfs fs/minix fs/ncpfs fs/ocfs2 fs/qnx4 fs/reiserfs \
       fs/romfs fs/sysv fs/udf fs/ufs fs/xfs"

net_mods="net/802 net/8021q net/9p net/appletalk net/atm net/ax25 \
       net/bluetooth net/dccp net/decnet net/ieee80211 net/ipx net/irda \
       net/mac80211 net/netrom net/rfkill net/rose net/sched net/tipc \
       net/wanrouter net/wireless"

driver_mods="drivers/auxdisplay drivers/net/appletalk \
       drivers/net/hamradio drivers/net/pcmcia drivers/net/tokenring \
       drivers/net/wireless drivers/net/irda drivers/atm drivers/usb/atm \
       drivers/acpi drivers/char/drm drivers/char/mwave \
       drivers/char/ipmp drivers/char/pcmcia drivers/crypto drivers/dca \
       drivers/firmware drivers/memstick drivers/mmc drivers/mfs \
       drivers/parport drivers/video drivers/watchdog drivers/net/ppp* \
       drivers/usb/serial drivers/usb/misc drivers/usb/class \
       drivers/usb/image drivers/rtc"

misc_mods="drivers/bluetooth drivers/firewire drivers/i2c drivers/isdn \
       drivers/media drivers/misc drivers/leds drivers/mtd drivers/w1 sound \
       drivers/input drivers/pcmcia drivers/scsi/pcmcia crypto lib"

for mods in $fs_mods $net_mods $misc_mods $driver_mods ; do
    $RM $MODULES/$mods
done

echo "Removing all timezones except for UTC"
find /usr/share/zoneinfo -regextype egrep -type f \
  ! -regex ".*/UTC|.*/GMT" -exec $RM {} \;

echo "Removing blacklisted files and directories"
blacklist="/boot /etc/alsa /etc/pki /usr/share/hwdata/MonitorsDB \
    /usr/share/hwdata/oui.txt /usr/share/hwdata/videoaliases \
    /usr/share/hwdata/videodrivers /usr/share/fedora-release \
    /usr/share/tabset /usr/share/libvirt /usr/share/augeas/lenses/tests \
    /usr/share/tc /usr/share/emacs /usr/share/info /usr/kerberos \
    /usr/src /usr/etc /usr/games /usr/include /usr/local \
    /usr/sbin/dell*"
blacklist_lib="/usr/lib{,64}/python2.5 /usr/lib{,64}/gconv \
    /usr/{,lib64}/tc /usr/lib{,64}/tls /usr/lib{,64}/sse2 \
    /usr/lib{,64}/pkgconfig /usr/lib{,64}/nss /usr/lib{,64}/X11 \
    /usr/lib{,64}/games /usr/lib{,64}/alsa-lib /usr/lib{,64}/fs/reiserfs \
    /usr/lib{,64}/krb5 /usr/lib{,64}/hal /usr/lib{,64}/gio \
    /lib/terminfo/d /lib/terminfo/v /lib/terminfo/a \
    /lib/firmware /usr/lib/locale /usr/lib/syslinux"
blacklist_pango="/usr/lib{,64}/pango /usr/lib{,64}/libpango* \
    /etc/pango /usr/bin/pango*"
blacklist_hal="/usr/bin/hal-device /usr/bin/hal-disable-polling \
    /usr/bin/hal-find-by-capability /usr/bin/hal-find-by-property \
    /usr/bin/hal-is-caller-locked-out /usr/bin/hal-is-caller-privileged \
    /usr/bin/hal-lock /usr/bin/hal-set-property /usr/bin/hal-setup-keymap"
blacklist_ssh="/usr/bin/sftp /usr/bin/slogin /usr/bin/ssh /usr/bin/ssh-add \
    /usr/bin/ssh-agent /usr/bin/ssh-copy-id /usr/bin/ssh-keyscan"
docs_blacklist="/usr/share/omf /usr/share/gnome /usr/share/doc \
    /usr/share/locale /usr/share/libthai /usr/share/man /usr/share/terminfo \
    /usr/share/X11 /usr/share/i18n"

$RM $blacklist $blacklist_lib $blacklist_pango $blacklist_hal $blacklist_ssh \
    $docs_blacklist

echo "Cleanup empty directory structures in /usr/share"
find /usr/share -type d -exec rmdir {} \; > /dev/null 2>&1

echo "Finished Kickstart Post"
