%define pbuild %{_builddir}/%{name}-%{version}
%define app_root %{_datadir}/%{name}

Summary: oVirt front end WUI
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
Requires: rubygem(krb5-auth) >= 0.6
Requires: ruby-gettext-package
Requires: postgresql-server
Requires: ruby-postgres
Requires: pwgen
Requires: httpd >= 2.0
Requires: mod_auth_kerb
Requires: ruby-libvirt >= 0.0.2
Requires: rrdtool-ruby
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
BuildArch: noarch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
URL: http://ovirt.org/

%description

The webapp for oVirt.

%prep
%setup -q

%build

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
touch %{buildroot}%{_localstatedir}/log/%{name}/host-status.log
%{__install} -p -m0644 %{pbuild}/conf/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d

%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-host-browser %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-host-status %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-host-collect %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-mongrel-rails %{buildroot}%{_initrddir}
%{__install} -Dp -m0755 %{pbuild}/conf/ovirt-taskomatic %{buildroot}%{_initrddir}

# copy over all of the src directory...
%{__cp} -a %{pbuild}/src/* %{buildroot}%{app_root}

# move configs to /etc, keeping symlinks for Rails
%{__mv} %{buildroot}%{app_root}/config/database.yml %{buildroot}%{_sysconfdir}/%{name}
%{__mv} %{buildroot}%{app_root}/config/ldap.yml %{buildroot}%{_sysconfdir}/%{name}
%{__mv} %{buildroot}%{app_root}/config/environments/development.rb %{buildroot}%{_sysconfdir}/%{name}
%{__mv} %{buildroot}%{app_root}/config/environments/production.rb %{buildroot}%{_sysconfdir}/%{name}
%{__mv} %{buildroot}%{app_root}/config/environments/test.rb %{buildroot}%{_sysconfdir}/%{name}
%{__ln_s} %{_sysconfdir}/%{name}/database.yml %{buildroot}%{app_root}/config
%{__ln_s} %{_sysconfdir}/%{name}/ldap.yml %{buildroot}%{app_root}/config
%{__ln_s} %{_sysconfdir}/%{name}/development.rb %{buildroot}%{app_root}/config/environments
%{__ln_s} %{_sysconfdir}/%{name}/production.rb %{buildroot}%{app_root}/config/environments
%{__ln_s} %{_sysconfdir}/%{name}/test.rb %{buildroot}%{app_root}/config/environments

# remove the files not needed for the installation
%{__rm} -f %{buildroot}%{app_root}/task-omatic/.gitignore

%{__cp} -a %{pbuild}/scripts/ovirt-add-host %{buildroot}%{_bindir}
%{__cp} -a %{pbuild}/scripts/ovirt-wui-install %{buildroot}%{_sbindir}
%{__rm} -rf %{buildroot}%{app_root}/tmp 
%{__mkdir} %{buildroot}%{_localstatedir}/lib/%{name}/tmp
%{__ln_s} %{_localstatedir}/lib/%{name}/tmp %{buildroot}%{app_root}/tmp

%clean
rm -rf $RPM_BUILD_ROOT

%pre
/usr/sbin/groupadd -r ovirt 2>/dev/null || :
/usr/sbin/useradd -g ovirt -c "oVirt" \
    -s /sbin/nologin -r -d /var/ovirt ovirt 2> /dev/null || :

%post
# script
%define daemon_chkconfig_post(d:) \
/sbin/chkconfig --list %{-d*} >& /dev/null \
LISTRET=$? \
/sbin/chkconfig --add %{-d*} \
if [ $LISTRET -ne 0 ]; then \
	/sbin/chkconfig %{-d*} on \
fi \
%{nil}

#removes obsolete services if present
if [ -e %{_initrddir}/ovirt-wui ] ; then
  /sbin/service ovirt-wui stop > /dev/null 2>&1
  /sbin/service ovirt-host-keyadd stop > /dev/null 2>&1
  /sbin/chkconfig --del ovirt-wui
  /sbin/chkconfig --del ovirt-host-keyadd
  %{__rm} %{_initrddir}/ovirt-wui
  %{__rm} %{_initrddir}/ovirt-host-keyadd
fi

# if this is the initial RPM install, then we want to turn the new services
# on; otherwise, we respect the choices the administrator already has made.
# check this by seeing if each daemon is already installed
%daemon_chkconfig_post -d ovirt-host-browser
%daemon_chkconfig_post -d ovirt-host-status
%daemon_chkconfig_post -d ovirt-host-collect
%daemon_chkconfig_post -d ovirt-mongrel-rails
%daemon_chkconfig_post -d ovirt-taskomatic

%preun
if [ "$1" = 0 ] ; then
  /sbin/service ovirt-host-browser stop > /dev/null 2>&1
  /sbin/service ovirt-host-status stop > /dev/null 2>&1
  /sbin/service ovirt-host-collect stop > /dev/null 2>&1
  /sbin/service ovirt-mongrel-rails stop > /dev/null 2>&1
  /sbin/service ovirt-taskomatic stop > /dev/null 2>&1
  /sbin/chkconfig --del ovirt-host-browser
  /sbin/chkconfig --del ovirt-host-status
  /sbin/chkconfig --del ovirt-host-collect
  /sbin/chkconfig --del ovirt-mongrel-rails
  /sbin/chkconfig --del ovirt-taskomatic
fi

%files
%defattr(-,root,root,0755)
%{_sbindir}/ovirt-wui-install
%{_bindir}/ovirt-add-host
%{_initrddir}/ovirt-host-browser
%{_initrddir}/ovirt-host-status
%{_initrddir}/ovirt-host-collect
%{_initrddir}/ovirt-mongrel-rails
%{_initrddir}/ovirt-taskomatic
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%doc
%attr(-, ovirt, ovirt) %{_localstatedir}/lib/%{name}
%attr(-, ovirt, ovirt) %{_localstatedir}/run/%{name}
%attr(-, ovirt, ovirt) %{_localstatedir}/log/%{name}
%{app_root}
%dir %{_sysconfdir}/%{name}
%dir %{_sysconfdir}/%{name}/db
%config(noreplace) %{_sysconfdir}/%{name}/database.yml
%config(noreplace) %{_sysconfdir}/%{name}/ldap.yml
%config(noreplace) %{_sysconfdir}/%{name}/development.rb
%config(noreplace) %{_sysconfdir}/%{name}/production.rb
%config(noreplace) %{_sysconfdir}/%{name}/test.rb

%changelog
* Thu May 29 2008 Alan Pevec <apevec@redhat.com> - 0.0.5-0
- use rubygem-krb5-auth

* Fri Nov  2 2007  <sseago@redhat.com> - 0.0.1-1
- Initial build.

