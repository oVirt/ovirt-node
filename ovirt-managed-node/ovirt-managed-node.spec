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
Requires:       libvirt
ExclusiveArch:  %{ix86} x86_64

%define app_root %{_datadir}/%{name}

%description
Provides a series of daemons and support utilities to allow an
oVirt managed node to interact with the oVirt server.

%prep

%setup -q
%{__rm} -rf %{buildroot}
mkdir %{buildroot}

%build
make

%install
%{__install} -d -m0755 %{buildroot}%{_sbindir}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/chkconfig.d
%{__install} -d -m0755 %{buildroot}%{_initrddir}
%{__install} -d -m0755 %{buildroot}%{app_root}

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

%{__install} -p -m0755 scripts/ovirt-setup %{buildroot}%{app_root}

%clean
%{__rm} -rf %{buildroot}

%post
/sbin/chkconfig --add ovirt-early
/sbin/chkconfig ovirt-early on
/sbin/chkconfig --add ovirt
/sbin/chkconfig ovirt on
/sbin/chkconfig --add ovirt-post
/sbin/chkconfig ovirt-post on

%{app_root}/ovirt-setup

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
%{app_root}/ovirt-setup
%defattr(-,root,root,0644)
%{_initrddir}/ovirt-functions
%{_sysconfdir}/collectd.conf.in
%{_sysconfdir}/chkconfig.d/collectd
%doc README NEWS AUTHOR ChangeLog

%changelog
* Mon Jun 30 2008 Perry Myers <pmyers@redhat.com> - 0.92 0.1
- Add in sections of kickstart post, general cleanup
