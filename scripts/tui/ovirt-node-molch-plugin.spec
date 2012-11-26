%if 0%{?rhel} && 0%{?rhel} <= 5
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif
%global date    %(date '+%Y%m%d%H%M%%S')
%global hash    %(cat scm_hash.txt)
%define upstream_name ovirt-node-molch

Name:           %{upstream_name}-plugin
Version:        0.0.1
Release:        1.git%{hash}%{?dist}
Summary:        oVirt Node plugin for an alternate config TUI

License:        GPLv2+
URL:            https://www.gitorious.org/ovirt/ovirt-node-config-molch
Source0:        dist/%{name}-git%{hash}.tar.gz

BuildArch:      noarch

BuildRequires:  python2-devel
Requires:       python-urwid
#Requires:       python-augeas
Requires:       python-gudev
Requires:       libvirt-python


%description
An alternate configuration TUI based on python-urwid supporting more
features.


%prep
%setup -q -n %{upstream_name}-%{version}


%build
# Nothing


%install
%makeinstall python=%{__python} prefix=%{_prefix} root=%{buildroot}
# Remove some extra data
rm -rf %{buildroot}/usr/extra


%check
# Nothing, yet


%files
%doc README
%{python_sitelib}/ovirt_node_molch*.egg-info
%{python_sitelib}/ovirt/__init__.*
%{python_sitelib}/ovirt/node/*
%{_bindir}/ovirt-config-setup
#%{_bindir}/ovirt-config-installer


%changelog
* Tue Oct 09 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 0.0.1-1
- Initial
