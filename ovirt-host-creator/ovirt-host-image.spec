Summary: oVirt Managed Node boot ISO image
Name: ovirt-host-image
Source1: version
Version: %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release: %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}
Source0: %{name}-%{version}.tar
License: Fedora
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
URL: http://ovirt.org/

%define app_root %{_datadir}/%{name}
%define tftpboot %{_var}/lib/tftpboot

#  disable debuginfo, makes no sense for boot image and it is created empty anyway
%define debug_package %{nil}

%description
The ISO boot image for oVirt Managed Node booting from CDROM device.
At the moment, this RPM just packages prebuilt ISO.

%package pxe
Summary: oVirt Managed Node boot PXE image
Group: Applications/System

%description pxe
The PXE boot image for oVirt Managed Node network boot from oVirt Admin Node.
At the moment, this RPM just packages prebuilt tftpboot folder.

%prep
%setup -q

%build

%install
%{__rm} -rf %{buildroot}
mkdir %{buildroot}

%{__install} -d -m0755 %{buildroot}%{tftpboot}
%{__install} -d -m0755 %{buildroot}%{tftpboot}/pxelinux.cfg
%{__install} -p -m0644 pxelinux.cfg/default %{buildroot}%{tftpboot}/pxelinux.cfg/default
%{__install} -p -m0644 pxelinux.0 %{buildroot}%{tftpboot}
%{__install} -p -m0644 initrd0.img %{buildroot}%{tftpboot}
%{__install} -p -m0644 vmlinuz0 %{buildroot}%{tftpboot}
%{__install} -d -m0755 %{buildroot}%{app_root}
%{__install} -p -m0644 ovirt.iso %{buildroot}%{app_root}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root)
%{app_root}/ovirt.iso

%files pxe
%defattr(-,root,root)
%config(noreplace) %{tftpboot}/pxelinux.cfg/default
%{tftpboot}/pxelinux.0
%{tftpboot}/initrd0.img
%{tftpboot}/vmlinuz0

%changelog
* Tue Jun 03 2008 Alan Pevec <apevec@redhat.com>  0.0.5-1
- Initial build.
