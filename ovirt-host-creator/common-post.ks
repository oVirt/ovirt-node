# -*-Shell-script-*-
echo "Starting Kickstart Post"
PATH=/sbin:/usr/sbin:/bin:/usr/bin
export PATH

echo "Creating shadow files"
# because we aren't installing authconfig, we aren't setting up shadow
# and gshadow properly.  Do it by hand here
pwconv
grpconv

echo "Re-creating cracklib dicts"
# cracklib-dicts is 8MB.  We probably don't need to have strict password
# checking on the ovirt host
# unfortunately we can't create an empty cracklib dict, so we create it
# with a single entry "1"
echo 1 | packer >& /dev/null

echo "Forcing C locale"
# force logins (via ssh, etc) to use C locale, since we remove locales
cat >> /etc/profile << \EOF
# oVirt: force our locale to C since we don't have locale stuff'
export LC_ALL=C LANG=C
EOF

# here, remove a bunch of files we don't need that are just eating up space.
# it breaks rpm slightly, but it's not too bad

echo "Removing excess RPMs"

# kernel pulls in mkinitrd which pulls in isomd5sum which pulls in python,
# and livecd-tools needs lokkit to disable SELinux.
# However, this is just an install-time dependency; we can remove
# it afterwards, which we do here
rpm -e system-config-firewall-tui system-config-network-tui rhpl \
    rpm-python dbus-python kudzu newt-python newt
rpm -e qemu kpartx mkinitrd isomd5sum dmraid python python-libs

# Sigh.  ntp has a silly dependency on perl because of auxiliary scripts which
# we don't need to use.  Forcibly remove it here
rpm -e --nodeps perl perl-libs perl-Module-Pluggable perl-version \
    perl-Pod-Simple perl-Pod-Escapes

RM="rm -rf"

echo "Removing docs and internationalization"
$RM /usr/share/omf
$RM /usr/share/gnome
$RM /usr/share/doc
$RM /usr/share/locale
$RM /usr/share/libthai
$RM /usr/share/man
$RM /usr/share/terminfo
$RM /usr/share/X11
$RM /usr/share/i18n

find /usr/share/zoneinfo -regextype egrep -type f \
  ! -regex ".*/UTC" -exec $RM {} \;
# XXX anaconda/timezone.py does it, missing in imgcreate/kickstart.py
cp /usr/share/zoneinfo/UTC /etc/localtime

$RM /usr/lib/locale
$RM /usr/lib/syslinux
$RM /usr/lib64/gconv
$RM /usr/lib64/pango
$RM /usr/lib64/libpango*
$RM /etc/pango
$RM /usr/bin/pango*

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
       net/wanrouter net/wireless drivers/auxdisplay drivers/net/appletalk \
       drivers/net/hamradio drivers/net/pcmcia drivers/net/tokenring \
       drivers/net/wireless drivers/net/irda drivers/atm drivers/usb/atm"

misc_mods="drivers/bluetooth drivers/firewire drivers/i2c drivers/isdn \
       drivers/media drivers/misc drivers/leds drivers/mtd drivers/w1 sound \
       drivers/input drivers/pcmcia drivers/scsi/pcmcia"

for mods in $fs_mods $net_mods $misc_mods ; do
    $RM $MODULES/$mods
done

echo "Finished Kickstart Post"
