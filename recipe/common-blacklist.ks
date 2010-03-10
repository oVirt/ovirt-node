# -*-Shell-script-*-
%post

echo "Removing excess RPMs"

# kernel pulls in mkinitrd which pulls in isomd5sum which pulls in python,
# and livecd-tools needs lokkit to configure SELinux.
# However, this is just an install-time dependency; we can remove
# it afterwards, which we do here
RPMS="system-config-firewall-tui system-config-network-tui rhpl \
    rpm-python kudzu libsemanage-python"

RPMS="$RPMS mkinitrd isomd5sum dmraid checkpolicy"

# Remove additional RPMs forcefully
RPMS="$RPMS gamin pm-utils kbd usermode vbetool ConsoleKit hdparm \
    efibootmgr linux-atm-libs fedora-release-notes \
    cryptsetup-luks pciutils mtools syslinux \
    wireless-tools radeontool libicu gnupg2 \
    fedora-logos"

# cronie pulls in exim (sendmail) which pulls in all kinds of perl deps
RPMS="$RPMS exim perl-version perl-Pod-Simple perl-libs perl-Module-Pluggable \
    perl-Pod-Escapes perl"

RPMS="$RPMS sysklogd"

# Things we could probably remove if libvirt didn't link against them
#RPMS="$RPMS avahi PolicyKit xen-libs"

# Things we could probably remove if qemu-kvm didn't link against them
#RPMS="$RPMS SDL alsa-lib"

# Pam complains when this is missing
#RPMS="$RPM ConsoleKit-libs"

for rpm in $RPMS; do
    rpm -v -e --nodeps $rpm 2> /dev/null
done

# the following are lists of kernel modules we are pretty sure we won't need;
# note that these can be single files or whole directories.  They are specified
# starting at $MODULES; so if you want to remove the NLS stuff from the
# fs subdir, your mods entry would be "fs/nls"
fs_mods="fs/nls fs/9p fs/affs fs/autofs fs/autofs4 fs/befs fs/bfs fs/cifs \
       fs/coda fs/cramfs fs/dlm fs/ecryptfs fs/efs fs/exportfs fs/ext4 \
       fs/freevxfs fs/gfs2 fs/hfs fs/hfsplus fs/jbd2 fs/jffs \
       fs/jffs2 fs/jfs fs/minix fs/ncpfs fs/ocfs2 fs/qnx4 fs/reiserfs \
       fs/romfs fs/sysv fs/udf fs/ufs fs/xfs"

net_mods="net/9p net/appletalk net/atm net/ax25 \
       net/bluetooth net/dccp net/decnet net/ieee80211 net/ipx net/irda \
       net/mac80211 net/netrom net/rfkill net/rose net/sched net/tipc \
       net/wanrouter net/wireless"

driver_mods="drivers/auxdisplay drivers/net/appletalk \
       drivers/net/hamradio drivers/net/pcmcia drivers/net/tokenring \
       drivers/net/wireless drivers/net/irda drivers/atm drivers/usb/atm \
       drivers/acpi drivers/char/drm drivers/char/mwave \
       drivers/char/ipmp drivers/char/pcmcia drivers/crypto \
       drivers/firmware drivers/memstick drivers/mmc drivers/mfs \
       drivers/parport drivers/video drivers/watchdog drivers/net/ppp* \
       drivers/usb/serial drivers/usb/misc drivers/usb/class \
       drivers/usb/image drivers/rtc drivers/char/lp*"

misc_mods="drivers/bluetooth drivers/firewire drivers/i2c drivers/isdn \
       drivers/media drivers/misc drivers/leds drivers/mtd drivers/w1 sound \
       drivers/input drivers/pcmcia drivers/scsi/pcmcia"

echo "Removing excess kernel modules"
MODULES="/lib/modules/*/kernel"
RM="rm -rf"

for mods in $fs_mods $net_mods $misc_mods $driver_mods ; do
    $RM $MODULES/$mods
done

echo "Removing all timezones except for UTC"
find /usr/share/zoneinfo -regextype egrep -type f \
  ! -regex ".*/UTC|.*/GMT" -exec $RM {} \;

echo "Removing blacklisted files and directories"
blacklist="/etc/alsa /etc/pki /usr/share/hwdata/MonitorsDB \
    /usr/share/hwdata/oui.txt /usr/share/hwdata/videoaliases \
    /usr/share/firstboot /usr/share/lua /usr/share/kde4 /usr/share/pixmaps \
    /usr/share/hwdata/videodrivers /usr/share/icons /usr/share/fedora-release \
    /usr/share/tabset /usr/share/libvirt /usr/share/augeas/lenses/tests \
    /usr/share/tc /usr/share/emacs /usr/share/info \
    /usr/src /usr/etc /usr/games /usr/include /usr/local \
    /usr/sbin/{dell*,sasldblistusers2,build-locale-archive,glibc_post_upgrade.*}"
blacklist_lib="/usr/{,lib64}/tc \
    /usr/lib{,64}/tls /usr/lib{,64}/sse2 \
    /usr/lib{,64}/pkgconfig /usr/lib{,64}/nss \
    /usr/lib{,64}/games /usr/lib{,64}/alsa-lib /usr/lib{,64}/fs/reiserfs \
    /usr/lib{,64}/krb5 /usr/lib{,64}/hal /usr/lib{,64}/gio \
    /usr/lib/locale /usr/lib/syslinux"
blacklist_pango="/usr/lib{,64}/pango /usr/lib{,64}/libpango* \
    /etc/pango /usr/bin/pango*"
blacklist_hal="/usr/bin/hal-disable-polling \
    /usr/bin/hal-is-caller-locked-out /usr/bin/hal-is-caller-privileged \
    /usr/bin/hal-lock /usr/bin/hal-set-property /usr/bin/hal-setup-keymap"
blacklist_ssh="/usr/bin/sftp /usr/bin/slogin /usr/bin/ssh /usr/bin/ssh-add \
    /usr/bin/ssh-agent /usr/bin/ssh-copy-id /usr/bin/ssh-keyscan"
blacklist_docs="/usr/share/omf /usr/share/gnome /usr/share/doc \
    /usr/share/locale /usr/share/libthai /usr/share/man \
    /usr/share/X11 /usr/share/i18n"

eval $RM $blacklist $blacklist_lib $blacklist_pango $blacklist_hal \
    $blacklist_ssh $blacklist_docs

echo "Cleanup empty directory structures in /usr/share"
find /usr/share -type d -exec rmdir {} \; > /dev/null 2>&1

echo "Cleanup excess selinux modules"
$RM /usr/share/selinux

echo "Removing python source files"
find / -name '*.py' -exec rm -f {} \;
find / -name '*.pyo' -exec rm -f {} \;

echo "Running image-minimizer..."
%end

%post --nochroot --interpreter image-minimizer
drop /usr/lib/libboost*
keep /usr/lib/libboost_program_options.so*
keep /usr/lib/libboost_filesystem.so*
keep /usr/lib/libboost_thread-mt.so*
keep /usr/lib/libboost_system.so*
drop /usr/lib64/libboost*
keep /usr/lib64/libboost_program_options.so*
keep /usr/lib64/libboost_filesystem.so*
keep /usr/lib64/libboost_thread-mt.so*
keep /usr/lib64/libboost_system.so*
drop /usr/kerberos
keep /usr/kerberos/bin/kinit
keep /usr/kerberos/bin/klist
drop /lib/firmware
keep /lib/firmware/3com
keep /lib/firmware/acenic
keep /lib/firmware/adaptec
keep /lib/firmware/advansys
keep /lib/firmware/bnx2
keep /lib/firmware/cxgb3
keep /lib/firmware/e100
keep /lib/firmware/myricom
keep /lib/firmware/qlogic
keep /lib/firmware/sun
keep /lib/firmware/tehuti
keep /lib/firmware/tigon
%end

