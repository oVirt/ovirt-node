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
Requires: livecd-tools >= 017
Requires: syslinux

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
BuildRequires: livecd-tools >= 017

%description pxe
The PXE boot image for oVirt Managed Node network boot from oVirt Admin Node.

%prep
%setup -q

%build
./ovirt-pxe ovirt.iso

%install
%{__rm} -rf %{buildroot}
mkdir %{buildroot}

%{__install} -d -m0755 %{buildroot}%{tftpboot}
%{__install} -d -m0755 %{buildroot}%{tftpboot}/pxelinux.cfg
%{__install} -p -m0644 tftpboot/pxelinux.cfg/default %{buildroot}%{tftpboot}/pxelinux.cfg/default
%{__install} -p -m0644 tftpboot/pxelinux.0 %{buildroot}%{tftpboot}
%{__install} -p -m0644 tftpboot/initrd0.img %{buildroot}%{tftpboot}
%{__install} -p -m0644 tftpboot/vmlinuz0 %{buildroot}%{tftpboot}
%{__install} -d -m0755 %{buildroot}%{app_root}
%{__install} -p -m0644 ovirt.iso %{buildroot}%{app_root}
%{__install} -d -m0755 %{buildroot}%{_sbindir}
%{__install} -p -m0755 ovirt-pxe %{buildroot}%{_sbindir}
%{__install} -p -m0755 ovirt-flash %{buildroot}%{_sbindir}
%{__install} -p -m0755 ovirt-flash-static %{buildroot}%{_sbindir}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,0644)
%{app_root}/ovirt.iso
%defattr(-,root,root,0755)
%{_sbindir}/ovirt-pxe
%{_sbindir}/ovirt-flash
%{_sbindir}/ovirt-flash-static

%files pxe
%defattr(-,root,root,0644)
%config(noreplace) %{tftpboot}/pxelinux.cfg/default
%{tftpboot}/pxelinux.0
%{tftpboot}/initrd0.img
%{tftpboot}/vmlinuz0

%changelog
* Thu Jul 03 2008 Perry Myers <pmyers@redhat.com> 0.92-0
- Only store ISO in SRPM, and generate PXE from that during build

* Tue Jun 03 2008 Alan Pevec <apevec@redhat.com>  0.0.5-1
- Initial build.


