Summary:        The managed node demons for oVirt.
Name:           ovirt-managed-node
Source1:        version
Version:        %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release:        %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}
Source0:        %{name}-%{version}.tar.gz
License:        GPL
Group:          Applications/System

BuildRoot:      %{_tmppath}/%{name}-%{version}-root
URL:            http://www.ovirt.org/
BuildRequires:  libvirt-devel
Requires:       libvirt
ExclusiveArch:  %{ix86} x86_64 ia64


%description
Provides a series of daemons and support utilities to allow an
oVirt managed node to interact with the oVirt server.


%prep
%setup

rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT


%build
make

mkdir -p $RPM_BUILD_ROOT/sbin
cp ovirt-awake         $RPM_BUILD_ROOT/sbin
cp ovirt-identify-node $RPM_BUILD_ROOT/sbin


%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(755,root,root)
%doc README NEWS AUTHOR ChangeLog
/sbin/ovirt-awake
/sbin/ovirt-identify-node
