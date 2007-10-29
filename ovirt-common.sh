create_iso() {
    LABEL=ovirt-`date +%Y%m%d%H%M`
    ./creator.py -c ovirt.ks -f $LABEL 1>&2
    echo $LABEL.iso
}