%include version.ks

# add RHEV-H rwtab locations
mkdir -p /rhev
cat > /etc/rwtab.d/rhev << EOF_RWTAB_RHEVH
dirs    /var/db
EOF_RWTAB_RHEVH

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

# remove errors from /sbin/dhclient-script
DHSCRIPT=/sbin/dhclient-script
sed -i 's/mv /cp -p /g'  $DHSCRIPT
sed -i '/rm -f.*${interface}/d' $DHSCRIPT
sed -i '/rm -f \/etc\/localtime/d' $DHSCRIPT
sed -i '/rm -f \/etc\/ntp.conf/d' $DHSCRIPT
sed -i '/rm -f \/etc\/yp.conf/d' $DHSCRIPT

# rhbz#734478 add virt-who (*.py are removed in rhevh image)
cat > /usr/bin/virt-who <<EOF_virt_who
#!/bin/sh
exec /usr/bin/python /usr/share/virt-who/virt-who.pyc "\$@"
EOF_virt_who

# set maxlogins to 3
echo "*        -       maxlogins      3" >> /etc/security/limits.conf

# dracut config
cat <<_EOF_ > /etc/dracut.conf.d/ovirt-node.conf

add_dracutmodules+="dmsquash-live"

_EOF_
