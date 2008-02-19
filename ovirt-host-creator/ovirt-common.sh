create_iso() {
    if [ $# -eq 0 ]; then
	LABEL=ovirt-`date +%Y%m%d%H%M`
	/usr/bin/livecd-creator -c ovirt.ks -f $LABEL 1>&2 &&
	echo $LABEL.iso
    elif [ $# -eq 1 ]; then
	/usr/bin/livecd-creator -c ovirt.ks -b $1 1>&2 &&
	echo $1
    else
	return 1
    fi
}
