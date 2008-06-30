PATH=/sbin:/bin:/usr/bin
export PATH

create_iso() {
    KICKSTART=ovirt.ks
    if [ $# -eq 0 ]; then
        LABEL=ovirt-`date +%Y%m%d%H%M`
        livecd-creator --skip-minimize -c $KICKSTART -f $LABEL 1>&2 &&
        echo $LABEL.iso
    elif [ $# -eq 1 ]; then
        livecd-creator --skip-minimize -c $KICKSTART -b $1 1>&2 &&
        echo $1
    else
        return 1
    fi
}
