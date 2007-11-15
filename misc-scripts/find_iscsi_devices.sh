#!/bin/bash
for sd in `ls -d /sys/block/sd*` ; do
        vendor=`cat $sd/device/vendor | sed -e 's/[ \t]*$//'`
        if [ "$vendor" = "IET" ]; then
                echo "ISCSI"
        fi
done
