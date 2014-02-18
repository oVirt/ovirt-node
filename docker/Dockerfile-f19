FROM mattdm/fedora
VOLUME ["/ovirt"]
RUN yum -y install install livecd-tools appliance-tools-minimizer
RUN yum -y install fedora-packager python-devel rpm-build createrepo
RUN yum -y install selinux-policy-doc checkpolicy selinux-policy-devel
RUN yum -y install autoconf automake python-mock python-lockfile

ADD ./buildovirt.sh /buildovirt.sh
ENTRYPOINT ["./buildovirt.sh"]
CMD ["master"]
