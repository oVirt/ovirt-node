# RHEL specific image minimization
droprpm cvs
droprpm gettext
droprpm hesiod
droprpm procmail
droprpm sendmail
drop /etc/rc.d/init.d/libvirt-guests
drop /var/lib/yum
drop /etc/yum.repos.d/C*
