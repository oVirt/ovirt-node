# ovirt-install-node-stateless
# ovirt_setup_libvirtd()
    # just to get a boot warning to shut up
    touch /etc/resolv.conf

    # make libvirtd listen on the external interfaces
    sed -i -e 's/^#\(LIBVIRTD_ARGS="--listen"\).*/\1/' \
       /etc/sysconfig/libvirtd

    # set up qemu daemon to allow outside VNC connections
    sed -i -e 's/^[[:space:]]*#[[:space:]]*\(vnc_listen = "0.0.0.0"\).*/\1/' \
       /etc/libvirt/qemu.conf
    # set up libvirtd to listen on TCP (for kerberos)
    sed -i -e "s/^[[:space:]]*#[[:space:]]*\(listen_tcp\)\>.*/\1 = 1/" \
       -e "s/^[[:space:]]*#[[:space:]]*\(listen_tls\)\>.*/\1 = 0/" \
       /etc/libvirt/libvirtd.conf

    # with libvirt (0.4.0), make sure we we setup gssapi in the mech_list
    sasl_conf=/etc/sasl2/libvirt.conf
    if ! grep -qE "^mech_list: gssapi" $sasl_conf ; then
       sed -i -e "s/^\([[:space:]]*mech_list.*\)/#\1/" $sasl_conf
       echo "mech_list: gssapi" >> $sasl_conf
    fi

#ovirt_setup_anyterm()
   # configure anyterm
   cat >> /etc/sysconfig/anyterm << \EOF_anyterm
ANYTERM_CMD="sudo /usr/bin/virsh console %p"
ANYTERM_LOCAL_ONLY=false
EOF_anyterm

   # permit it to run the virsh console
   echo "anyterm ALL=NOPASSWD: /usr/bin/virsh console *" >> /etc/sudoers

