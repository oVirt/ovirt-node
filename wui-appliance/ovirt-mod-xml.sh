#!/bin/bash

TMPFILE=`mktemp`

virsh -c qemu:///system dumpxml developer > $TMPFILE &&

perl -ni -e '$m = m!</interface>!; print; $m and print ' \
	-e 'qq(    <interface type="bridge">\n) .'             \
	-e 'qq(      <mac address="00:16:3e:12:34:56"/>\n) .'  \
	-e 'qq(      <source bridge="dummybridge"/>\n) .'      \
	-e 'qq(    </interface>\n)' $TMPFILE &&

virsh -c qemu:///system define $TMPFILE
rm -f $TMPFILE
