#!/bin/bash

# Remove the temporary file on exit or signal.
trap 'st=$?; rm -rf "$tmpfile" && exit $st' 0
trap 'exit $?' 1 2 13 15

tmpfile=`mktemp` || exit 1

virsh -c qemu:///system dumpxml developer > "$tmpfile" || exit 1

mac=00:16:3e:12:34:56

# If this MAC address is already in the XML, stop now.
grep $mac "$tmpfile" > /dev/null &&
  { echo 1>&2 "$0: you seem to have already run this script"; exit 1; }

err=1
# Add an interface block right after the only existing one.
perl -ni -e '$m = m!</interface>!; print; $m and print '   \
	 -e 'qq(    <interface type="bridge">\n) .'        \
	 -e 'qq(      <mac address="'$mac'"/>\n) .'        \
	 -e 'qq(      <source bridge="dummybridge"/>\n) .' \
	 -e 'qq(    </interface>\n)' "$tmpfile" &&
virsh -c qemu:///system define "$tmpfile" && err=0

exit $err
