%include version.ks

# According with man systemd-journald.service:
# By default, the journal stores log data in /run/log/journal/.
# Since /run/ is volatile, log data is lost at reboot. To make the data
# persistent, it is sufficient to create /var/log/journal/ where
# systemd-journald will then store the data
install -dm 0755 /var/log/journal

# patch kdumpctl so "net" still works for now
# can remove when rhbz#1139298 lands
# rhbz#1095140
patch -d /bin -p0 << \EOF_kdump
--- kdumpctl       2014-09-28 17:24:41.744858571 +0000
+++ kdumpctl       2014-09-28 17:24:28.251942734 +0000
@@ -242,7 +242,7 @@
		case "$config_opt" in
		#* | "")
			;;
-		raw|ext2|ext3|ext4|minix|btrfs|xfs|nfs|ssh|sshkey|path|core_collector|kdump_post|kdump_pre|extra_bins|extra_modules|default|force_rebuild|dracut_args|fence_kdump_args|fence_kdump_nodes)
+		raw|ext2|ext3|ext4|minix|btrfs|xfs|nfs|net|ssh|sshkey|path|core_collector|kdump_post|kdump_pre|extra_bins|extra_modules|default|force_rebuild|dracut_args|fence_kdump_args|fence_kdump_nodes)
			[ -z "$config_val" ] && {
				echo "Invalid kdump config value for option $config_opt."
				return 1;
@@ -476,6 +476,9 @@
		ssh)
			DUMP_TARGET=$config_val
			;;
+		net)
+			DUMP_TARGET=$config_val
+			;;
		*)
			;;
		esac
EOF_kdump

# include dmsquash-live in dracut for kdump
sed -ie 's/^#add_dracutmodules+=""/add_dracutmodules+="dmsquash-live"/' /etc/dracut.conf

# Make dmsquash-live able to be included on hostonly configurations
patch -d /usr/lib/dracut/modules.d/90dmsquash-live -p0 << \EOF_dmsquash
--- module-setup.sh        2015-01-13 07:29:57.907325412 -0700
+++ module-setup.sh        2015-01-13 07:30:08.900364143 -0700
@@ -3,8 +3,6 @@
 # ex: ts=8 sw=4 sts=4 et filetype=sh

 check() {
-    # a live host-only image doesn't really make a lot of sense
-    [[ $hostonly ]] && return 1
     return 255
 }
EOF_dmsquash

# add RHEV-H rwtab locations
mkdir -p /rhev
cat > /etc/rwtab.d/rhev << EOF_RWTAB_RHEVH
dirs    /var/db
EOF_RWTAB_RHEVH

# disable lvmetad rhbz#1147217
# Since we can't be sure of what values the LVM developers will use in the
# future or whether they'll comment out configuration and leave it to defaults,
# be as judicious as possible. Current defaults are in the format
# "^\s*#\s*option", so try to match that and strip off the comment if it's
# commented by default
#
# See thin_check_executable in lvm.conf(as of 20140101) for an example of
# possible defaults
#
# Match any whitespace with an optional #, then grab anything after that to
# use as a backreference
sed -ie 's/^\(\s*\)#*\(\s*use_lvmetad\)\s*=\s*[[:digit:]]\+/\1\2 = 0/' \
    /etc/lvm/lvm.conf

enabled=$(grep -q -E '^\s*use_lvmetad = 0$' /etc/lvm/lvm.conf)
if [ -n "$enabled" ]; then
    echo -e "lvmetad not disabled. use_lvmetad appears in lvm.conf at:\n"
    # Grab every instance in the file just in case for for output to see if
    # recommended usage has changed in the comments or the option disappeared
    # or other
    grep -E 'use_lvmetad' /etc/lvm/lvm.conf
    exit 1
fi

systemctl disable lvm2-lvmetad
systemctl disable lvm2-lvmetad.socket

# Disable ksmtuned, becuase it conflicts with vdsmd
# https://bugzilla.redhat.com/show_bug.cgi?id=1156369
systemctl disable ksmtuned.service
systemctl disable ksm.service

# minimal lsb_release for bz#549147
cat > /usr/bin/lsb_release <<\EOF_LSB
#!/bin/sh
if [ "$1" = "-r" ]; then
    printf "Release:\t$(cat /etc/rhev-hypervisor-release | awk '{print $7}')\n"
else
    echo RedHatEnterpriseVirtualizationHypervisor
fi
EOF_LSB
chmod +x /usr/bin/lsb_release

# CPE name rhbz#593463
MAJORVER=${VERSION%%.*}
MINORVER=${VERSION##*.}
cat > /etc/system-release-cpe <<EOF_CPE
cpe:/o:redhat:enterprise_linux:${MAJORVER}:update${MINORVER}:hypervisor${TYPE}
EOF_CPE

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
# vdsm
-A INPUT -p tcp --dport 54321 -j ACCEPT
# libvirt tls
-A INPUT -p tcp --dport 16514 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# gluster
-A INPUT -p tcp --dport 24007 -j ACCEPT
-A INPUT -p tcp --dport 24009:24109 -j ACCEPT
# guest consoles
-A INPUT -p tcp -m multiport --dports 5900:6923 -j ACCEPT
# migration
-A INPUT -p tcp -m multiport --dports 49152:49216 -j ACCEPT
# snmp
-A INPUT -p udp --dport 161 -j ACCEPT
#
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -m physdev ! --physdev-is-bridged -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOF

# configure IPv6 firewall, default is all ACCEPT
cat > /etc/sysconfig/ip6tables << \EOF
# oVirt automatically generated firewall configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p ipv6-icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
# vdsm
-A INPUT -p tcp --dport 54321 -j ACCEPT
# libvirt tls
-A INPUT -p tcp --dport 16514 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# guest consoles
-A INPUT -p tcp -m multiport --dports 5900:6923 -j ACCEPT
# migration
-A INPUT -p tcp -m multiport --dports 49152:49216 -j ACCEPT
# snmp
-A INPUT -p udp --dport 161 -j ACCEPT
# unblock ipv6 dhcp response
-A INPUT -p udp --dport 546 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp6-adm-prohibited
-A FORWARD -m physdev ! --physdev-is-bridged -j REJECT --reject-with icmp6-adm-prohibited
COMMIT
EOF

# remove errors from /sbin/dhclient-script
DHSCRIPT=/sbin/dhclient-script
sed -i 's/mv /cp -p /g'  $DHSCRIPT
sed -i '/rm -f.*${interface}/d' $DHSCRIPT
sed -i '/rm -f \/etc\/localtime/d' $DHSCRIPT
sed -i '/rm -f \/etc\/ntp.conf/d' $DHSCRIPT
sed -i '/rm -f \/etc\/yp.conf/d' $DHSCRIPT

# bz#1095138 - replace dirs with files to keep everything below /var/lib/nfs
sed -ie '/dirs[ \t].*nfs/ d' /etc/rwtab
echo "files     /var/lib/nfs" >> /etc/rwtab

# set maxlogins to 3
echo "*        -       maxlogins      3" >> /etc/security/limits.conf

# dracut config
cat <<_EOF_ > /etc/dracut.conf.d/ovirt-node.conf

add_dracutmodules+=" dmsquash-live "

_EOF_

patch --ignore-whitespace -d /usr/lib/dracut/ -p0 << \EOF_dracut
--- modules.d/90dmsquash-live/dmsquash-live-genrules.sh
+++ modules.d/90dmsquash-live/dmsquash-live-genrules.sh
@@ -3,10 +3,10 @@
 case "$root" in
   live:/dev/*)
     {
-        printf 'KERNEL=="%s", RUN+="/sbin/initqueue --settled --onetime --unique /sbin/dmsquash-live-root $env{DEVNAME}"\n' \
-            ${root#live:/dev/}
-        printf 'SYMLINK=="%s", RUN+="/sbin/initqueue --settled --onetime --unique /sbin/dmsquash-live-root $env{DEVNAME}"\n' \
-            ${root#live:/dev/}
+        printf 'KERNEL=="%s", RUN+="/sbin/initqueue --settled --onetime --unique /sbin/dmsquash-live-root %s"\n' \
+            "${root#live:/dev/}" "${root#live:}"
+        printf 'SYMLINK=="%s", RUN+="/sbin/initqueue --settled --onetime --unique /sbin/dmsquash-live-root %s"\n' \
+            "${root#live:/dev/}" "${root#live:}"
     } >> /etc/udev/rules.d/99-live-squash.rules
     wait_for_dev -n "${root#live:}"
   ;;
EOF_dracut

# rhbz 1162699 setting correct theme
/usr/sbin/plymouth-set-default-theme text
rm -rf /var/lib/sfcb/registration/repository.previous/root/virt

# rhbz 1181987 removing plymouth dracut message
sed -i 's/ln -sf initrd-release $initdir\/etc\/os-release/cp \/etc\/os-release $initdir\/etc\//' /lib/dracut/modules.d/99base/module-setup.sh

#we need network manager CLI but  (maybe) but not it service
systemctl disable NetworkManager

# FIXME Hack around bug https://bugzilla.redhat.com/show_bug.cgi?id=1286242
# Bug-Url: https://bugzilla.redhat.com/show_bug.cgi?id=1263648
sed -i "/MountFlags/ s/^/#/" /usr/lib/systemd/system/systemd-udevd.service
