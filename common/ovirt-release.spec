Summary:        ovirt.org Repository Configuration
Name:           ovirt-release
Source0:        ovirt.repo
Source1:        version
Version:        %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release:        %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}
License:        GPLv2
Group:          System Environment/Base
URL:            http://ovirt.org
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

%description
ovirt.org Repository contains packages and fixes required for oVirt
which are not yet in Fedora.

%prep
%setup -c -T

%build

%install
%{__rm} -rf %{buildroot}

install -dm 755 %{buildroot}/%{_sysconfdir}/yum.repos.d
install -pm 644 %{SOURCE0} %{buildroot}/%{_sysconfdir}/yum.repos.d


%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%config %{_sysconfdir}/yum.repos.d/*

%changelog
* Tue Jul 29 2008 Alan Pevec <apevec@redhat.com> 0.91-1
- Initial build.
