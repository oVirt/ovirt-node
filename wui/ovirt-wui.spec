%define pbuild %{_builddir}/%{name}-%{version}
%define app_root %{_datadir}/%{name}

Summary: Ovirt front end WUI
Name: ovirt-wui
Source1: version
Version: %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release: %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}
Source0: %{name}-%{version}.tar.gz
#Entire source code is GPL except for vendor/plugins/will_paginate and 
#vendor/plugins/betternestedset, which are MIT, and
#public/javascripts/jquery.*, which is both MIT and GPL
License: GPL and MIT
Group: Applications/System
Requires: ruby >= 1.8.1
Requires: ruby(abi) = 1.8
Requires: rubygem(activeldap) >= 0.10.0
Requires: rubygem(rails) >= 2.0.1
Requires: rubygem(mongrel) >= 1.0.1
Requires: rubygem(kerberos) >= 0.4
Requires: rubygem(hoe) >= 1.5.1
Requires: rubygem(rubyforge) >= 0.4.4
Requires: rubygem(activeldap) >= 0.10.0
Requires: ruby-gettext-package
Requires: postgresql-server
Requires: ruby-postgres
Requires: pwgen
Requires: httpd >= 2.0
Requires: mod_auth_kerb
Requires: ruby-libvirt >= 0.0.2
Requires: iscsi-initiator-utils
Requires: cyrus-sasl-gssapi
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
BuildRequires: ruby >= 1.8.1
BuildRequires: ruby-devel
BuildRequires: ruby-gettext-package
BuildRequires: rubygem(rake) >= 0.7
BuildRequires: avahi-devel
Provides: ovirt-wui
BuildArch: i386 x86_64
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
URL: http://ovirt.et.redhat.com

%description

The webapp for Ovirt.

%prep
%setup -q

%build

# make sure we override the DBWRITER_PATH with where it will actually be in
# the end; yes, this is ugly
CFLAGS="-DDBWRITER_PATH=\\\"/usr/share/ovirt-wui/host-browser/dbwriter.rb\\\"" make -C src/host-browser

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
mkdir %{buildroot}

%{__install} -d -m0755 %{buildroot}%{_bindir}
%{__install} -d -m0755 %{buildroot}%{_sbindir}
%{__install} -d -m0755 %{buildroot}%{_initrddir}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/httpd/conf.d
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/sysconfig/%{name}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/%{name}
%{__install} -d -m0755 %{buildroot}%{_sysconfdir}/%{name}/db
%{__install} -d -m0755 %{buildroot}%{_localstatedir}/lib/%{name}
%{__install} -d -m0755 %{buildroot}%{_localstatedir}/log/%{name}
%{__install} -d -m0755 %{buildroot}%{_localstatedir}/run/%{name}
%{__install} -d -m0755 %{buildroot}%{app_root}

touch %{buildroot}%{_localstatedir}/log/%{name}/mongrel.log
touch %{buildroot}%{_localstatedir}/log/%{name}/rails.log
touch %{buildroot}%{_localstatedir}/log/%{name}/taskomatic.log
touch %{buildroot}%{_localstatedir}/log/%{name}/host-keyadd.log
touch %{buildroot}%{_localstatedir}/log/%{name}/host-status.log
%{__install} -p -m0644 %{pbuild}/conf/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d

%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-host-browser %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-host-keyadd %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-host-status %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-mongrel-rails %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-taskomatic %{buildroot}%{_initrddir}

# copy over all of the src directory...
%{__cp} -a %{pbuild}/src/* %{buildroot}%{app_root}

# remove the files not needed for the installation
%{__rm} -f %{buildroot}%{app_root}/host-browser/Makefile
%{__rm} -f %{buildroot}%{app_root}/host-browser/.gitignore
%{__rm} -f %{buildroot}%{app_root}/host-browser/*.o
%{__rm} -f %{buildroot}%{app_root}/host-browser/*.c
%{__rm} -f %{buildroot}%{app_root}/task-omatic/.gitignore

%{__cp} -a %{pbuild}/scripts/ovirt-add-host %{buildroot}%{_bindir}
%{__cp} -a %{pbuild}/scripts/ovirt-wui-install %{buildroot}%{_sbindir}
%{__cp} -a %{pbuild}/scripts/ovirt-fix-ipa %{buildroot}%{_bindir}
%{__rm} -rf %{buildroot}%{app_root}/tmp 
%{__mkdir} %{buildroot}%{_localstatedir}/lib/%{name}/tmp
%{__ln_s} %{_localstatedir}/lib/%{name}/tmp %{buildroot}%{app_root}/tmp

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,0755)
%{_sbindir}/ovirt-wui-install
%{_bindir}/ovirt-add-host
%{_bindir}/ovirt-fix-ipa
%{_initrddir}/ovirt-host-browser
%{_initrddir}/ovirt-host-keyadd
%{_initrddir}/ovirt-host-status
%{_initrddir}/ovirt-mongrel-rails
%{_initrddir}/ovirt-taskomatic
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%doc
%attr(-, ovirt, ovirt) %{_localstatedir}/lib/%{name}
%attr(-, ovirt, ovirt) %{_localstatedir}/run/%{name}
%attr(-, ovirt, ovirt) %{_localstatedir}/log/%{name}
%{app_root}
%dir /etc/ovirt-wui
%defattr(2770,postgres,postgres)
%dir /etc/ovirt-wui/db

%pre
/usr/sbin/groupadd -r ovirt 2>/dev/null || :
/usr/sbin/useradd -g ovirt -c "Ovirt" \
    -s /sbin/nologin -r -d /var/ovirt ovirt 2> /dev/null || :

%post
#removes legacy ovirt-wui script if present
if [ -e %{_initrddir}/ovirt-wui ] ; then
  /sbin/service ovirt-wui stop > /dev/null 2>&1
  /sbin/chkconfig --del ovirt-wui
  %{__rm} %{_initrddir}/ovirt-wui
fi

exit 0

%preun
if [ "$1" = 0 ] ; then
  /sbin/service ovirt-host-browser stop > /dev/null 2>&1
  /sbin/service ovirt-host-keyadd stop > /dev/null 2>&1
  /sbin/service ovirt-host-status stop > /dev/null 2>&1
  /sbin/service ovirt-mongrel-rails stop > /dev/null 2>&1
  /sbin/service ovirt-taskomatic stop > /dev/null 2>&1
  /sbin/chkconfig --del ovirt-host-browser
  /sbin/chkconfig --del ovirt-host-keyadd
  /sbin/chkconfig --del ovirt-host-status
  /sbin/chkconfig --del ovirt-mongrel-rails
  /sbin/chkconfig --del ovirt-taskomatic
fi
%changelog
* Fri Nov  2 2007  <sseago@redhat.com> - 0.0.1-1
- Initial build.

