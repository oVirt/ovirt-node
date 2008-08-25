Summary:        The managed node daemons/scripts for oVirt
Name:           ovirt-managed-node
Source1:        version
Version:        %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release:        %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}
Source0:        %{name}-%{version}.tar.gz
License:        GPL
Group:          Applications/System

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-buildroot
URL:            http://www.ovirt.org/
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
BuildRequires:  libvirt-devel
BuildRequires:  dbus-devel hal-devel
Requires:       libvirt
Requires:       hal
ExclusiveArch:  %{ix86} x86_64

%define app_root %{_datadir}/%{name}

%description
Provides a series of daemons and support utilities to allow an
oVirt managed node to interact with the oVirt server.

%prep

%setup -q

%build
make

%install
%{__rm} -rf %{buildroot}
%{__install} -d -m0755 %{buildroot}%{_sbindir}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/chkconfig.d
%{__install} -d -m0755 %{buildroot}%{_initrddir}
%{__install} -d -m0755 %{buildroot}%{app_root}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/cron.hourly
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/logrotate.d

%{__install} -p -m0755 scripts/ovirt-awake %{buildroot}%{_sbindir}
%{__install} -p -m0755 ovirt-identify-node %{buildroot}%{_sbindir}

%{__install} -p -m0644 scripts/ovirt-functions %{buildroot}%{_initrddir}
%{__install} -p -m0755 scripts/ovirt-early %{buildroot}%{_initrddir}
%{__install} -p -m0755 scripts/ovirt %{buildroot}%{_initrddir}
%{__install} -p -m0755 scripts/ovirt-post %{buildroot}%{_initrddir}

%{__install} -p -m0644 scripts/collectd %{buildroot}%{_sysconfdir}/chkconfig.d
%{__install} -p -m0644 scripts/collectd.conf.in %{buildroot}%{_sysconfdir}
%{__install} -p -m0755 scripts/kvm-ifup %{buildroot}%{_sysconfdir}
%{__install} -p -m0755 scripts/dhclient-exit-hooks %{buildroot}%{_sysconfdir}

%{__install} -p -m0755 logrotate/ovirt-logrotate %{buildroot}%{_sysconfdir}/cron.hourly
%{__install} -p -m0644 logrotate/ovirt-logrotate.conf %{buildroot}%{_sysconfdir}/logrotate.d

echo "oVirt Managed Node release %{version}-%{release}" > %{buildroot}%{_sysconfdir}/ovirt-release

%clean
%{__rm} -rf %{buildroot}

%post
/sbin/chkconfig --add ovirt-early
/sbin/chkconfig ovirt-early on
/sbin/chkconfig --add ovirt
/sbin/chkconfig ovirt on
/sbin/chkconfig --add ovirt-post
/sbin/chkconfig ovirt-post on
/sbin/chkconfig --add collectd
/sbin/chkconfig collectd on

# just to get a boot warning to shut up
touch /etc/resolv.conf

# make libvirtd listen on the external interfaces
sed -i -e "s/^#\(LIBVIRTD_ARGS=\"--listen\"\).*/\1/" /etc/sysconfig/libvirtd

# set up qemu daemon to allow outside VNC connections
sed -i -e "s/^[[:space:]]*#[[:space:]]*\(vnc_listen = \"0.0.0.0\"\).*/\1/" \
    /etc/libvirt/qemu.conf

# set up libvirtd to listen on TCP (for kerberos)
sed -i -e "s/^[[:space:]]*#[[:space:]]*\(listen_tcp\)\>.*/\1 = 1/" \
    -e "s/^[[:space:]]*#[[:space:]]*\(listen_tls\)\>.*/\1 = 0/" \
    /etc/libvirt/libvirtd.conf

# make sure we don't autostart virbr0 on libvirtd startup
rm -f /etc/libvirt/qemu/networks/autostart/default.xml

# with the new libvirt (0.4.0), make sure we we setup gssapi in the mech_list
if [ `egrep -c "^mech_list: gssapi" /etc/sasl2/libvirt.conf` -eq 0 ]; then
    sed -i -e "s/^\([[:space:]]*mech_list.*\)/#\1/" /etc/sasl2/libvirt.conf
    echo "mech_list: gssapi" >> /etc/sasl2/libvirt.conf
fi

# remove the /etc/krb5.conf file; it will be fetched on bootup
rm -f /etc/krb5.conf

g=$(printf '\33[1m\33[32m')    # similar to g=$(tput bold; tput setaf 2)
n=$(printf '\33[m')            # similar to n=$(tput sgr0)
cat <<EOF > /etc/issue

           888     888 ${g}d8b$n         888
           888     888 ${g}Y8P$n         888
           888     888             888
   .d88b.  Y88b   d88P 888 888d888 888888
  d88''88b  Y88b d88P  888 888P'   888
  888  888   Y88o88P   888 888     888
  Y88..88P    Y888P    888 888     Y88b.
   'Y88P'      Y8P     888 888      'Y888

  Managed Node release %{version}-%{release}

  Virtualization just got the ${g}Green Light$n

EOF
cp -p /etc/issue /etc/issue.net

%preun
if [ "$1" = 0 ] ; then
  /sbin/chkconfig --del ovirt-early
  /sbin/chkconfig --del ovirt
  /sbin/chkconfig --del ovirt-post
fi

%files
%defattr(-,root,root,0755)
%{_sbindir}/ovirt-awake
%{_sbindir}/ovirt-identify-node
%{_initrddir}/ovirt-early
%{_initrddir}/ovirt
%{_initrddir}/ovirt-post
%{_sysconfdir}/kvm-ifup
%{_sysconfdir}/dhclient-exit-hooks
%config %{_sysconfdir}/logrotate.d/ovirt-logrotate.conf
%config %{_sysconfdir}/cron.hourly/ovirt-logrotate
%defattr(-,root,root,0644)
%{_initrddir}/ovirt-functions
%{_sysconfdir}/collectd.conf.in
%{_sysconfdir}/chkconfig.d/collectd
%config %attr(0644,root,root) %{_sysconfdir}/ovirt-release
%doc README NEWS AUTHOR ChangeLog

%changelog
* Tue Jul 29 2008 Perry Myers <pmyers@redhat.com> - 0.92 0.2
- Added /etc/ovirt-release and merged ovirt-setup into spec file

* Wed Jul 02 2008 Darryl Pierce <dpierce@redhat.com> - 0.92 0.2
- Added log rotation to limit file system writes.

* Mon Jun 30 2008 Perry Myers <pmyers@redhat.com> - 0.92 0.1
- Add in sections of kickstart post, general cleanup
