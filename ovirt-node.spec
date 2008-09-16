Summary:        The oVirt Node daemons/scripts
Name:           ovirt-node
Source1:        version
Version:        %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release:        %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}%{?extra_release}
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
Requires:       collectd
Requires:       cyrus-sasl-gssapi
ExclusiveArch:  %{ix86} x86_64

%define app_root %{_datadir}/%{name}

%description
Provides a series of daemons and support utilities to allow an
oVirt Node to interact with the oVirt server.

%prep

%setup -q

%build
%configure
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
%{__install} -p -m0755 ovirt-identify-node/ovirt-identify-node %{buildroot}%{_sbindir}
%{__install} -p -m0755 ovirt-listen-awake/ovirt-listen-awake %{buildroot}%{_sbindir}
%{__install} -Dp -m0755 ovirt-listen-awake/ovirt-listen-awake.init %{buildroot}%{_initrddir}/ovirt-listen-awake
%{__install} -Dp -m0755 ovirt-listen-awake/ovirt-install-node %{buildroot}%{_sbindir}
%{__install} -Dp -m0755 ovirt-listen-awake/ovirt-uninstall-node %{buildroot}%{_sbindir}


%{__install} -p -m0644 scripts/ovirt-functions %{buildroot}%{_initrddir}
%{__install} -p -m0755 scripts/ovirt-early %{buildroot}%{_initrddir}
%{__install} -p -m0755 scripts/ovirt %{buildroot}%{_initrddir}
%{__install} -p -m0755 scripts/ovirt-post %{buildroot}%{_initrddir}

%{__install} -p -m0644 scripts/collectd %{buildroot}%{_sysconfdir}/chkconfig.d
%{__install} -p -m0644 scripts/collectd.conf.in %{buildroot}%{_sysconfdir}

%{__install} -p -m0755 logrotate/ovirt-logrotate %{buildroot}%{_sysconfdir}/cron.hourly
%{__install} -p -m0644 logrotate/ovirt-logrotate.conf %{buildroot}%{_sysconfdir}/logrotate.d

echo "oVirt Node release %{version}-%{release}" > %{buildroot}%{_sysconfdir}/ovirt-release

%clean
%{__rm} -rf %{buildroot}

%post
/sbin/chkconfig --add ovirt-early
/sbin/chkconfig --add ovirt
/sbin/chkconfig --add ovirt-post
# this is ugly; we need collectd to start *after* libvirtd, so we own the
# /etc/chkconfig.d/collectd file, and then have to re-define collectd here
/sbin/chkconfig --add collectd
/sbin/chkconfig --add ovirt-listen-awake

%preun
if [ "$1" = 0 ] ; then
  /sbin/chkconfig --del ovirt-early
  /sbin/chkconfig --del ovirt
  /sbin/chkconfig --del ovirt-post
  /sbin/chkconfig --del ovirt-listen-awake
fi

%files
%defattr(-,root,root,0755)
%{_sbindir}/ovirt-awake
%{_sbindir}/ovirt-identify-node
%{_sbindir}/ovirt-listen-awake
%{_sbindir}/ovirt-install-node
%{_sbindir}/ovirt-uninstall-node
%{_initrddir}/ovirt-early
%{_initrddir}/ovirt
%{_initrddir}/ovirt-post
%{_initrddir}/ovirt-listen-awake
%config %{_sysconfdir}/logrotate.d/ovirt-logrotate.conf
%config %{_sysconfdir}/cron.hourly/ovirt-logrotate
%defattr(-,root,root,0644)
%{_initrddir}/ovirt-functions
%{_sysconfdir}/collectd.conf.in
%{_sysconfdir}/chkconfig.d/collectd
%config %attr(0644,root,root) %{_sysconfdir}/ovirt-release
%doc ovirt-identify-node/README ovirt-identify-node/NEWS
%doc ovirt-identify-node/AUTHOR ovirt-identify-node/ChangeLog
%doc ovirt-identify-node/COPYING

%changelog
* Thu Sep 11 2008 Chris Lalancette <clalance@redhat.com> - 0.92 0.7
- Add the ovirt-install- and ovirt-uninstall-node scripts, and refactor
  post to accomodate

* Mon Sep  8 2008 Jim Meyering <meyering@redhat.com> - 0.92 0.6
- Update ovirt-identify-node's build rule.

* Fri Aug 22 2008 Chris Lalancette <clalance@redhat.com> - 0.92 0.5
- Add the ovirt-listen-awake daemon to the RPM

* Fri Aug 22 2008 Chris Lalancette <clalance@redhat.com> - 0.92 0.4
- Re-arrange the directory layout, in preparation for ovirt-listen-awake

* Tue Jul 29 2008 Perry Myers <pmyers@redhat.com> - 0.92 0.2
- Added /etc/ovirt-release and merged ovirt-setup into spec file

* Wed Jul 02 2008 Darryl Pierce <dpierce@redhat.com> - 0.92 0.2
- Added log rotation to limit file system writes.

* Mon Jun 30 2008 Perry Myers <pmyers@redhat.com> - 0.92 0.1
- Add in sections of kickstart post, general cleanup
