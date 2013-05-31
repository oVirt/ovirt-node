%post
echo -n "Creating manifest"
# Create post-image processing manifests
rpm -qa --qf '%{name}-%{version}-%{release}.%{arch} (%{SIGPGP:pgpsig})\n' | \
    sort > /manifest-rpm.txt
rpm -qa --qf '%{sourcerpm}\n' | sort -u > /manifest-srpm.txt
# collect all included licenses rhbz#601927
rpm -qa --qf '%{license}\n' | sort -u > /manifest-license.txt
# dependencies
rpm -qa | xargs -n1 rpm -e --test 2> /manifest-deps.txt
echo -n "."

# Takes about 4min
#find / -xdev -print -exec rpm -qf {} \; > /manifest-owns.txt
# Alternative takes about 8sec, results are slightly different
{
    # Get all owned files
    rpm -qa | while read PKG
    do
        rpm -ql $PKG | while read FIL
        do
            [[ -e "$FIL" ]] && echo $FIL
        done | sed "s#\$#\t\t\t$PKG#"
    done
    # Get all files on fs and mark them as not owned
    find / -xdev | sed "s#\$#\t\t\tNot owned by any package.#"
# Just keep the first occurence of a file entry
# Unowned files will just occur once,
# owned once twice (just the firts entry is kept)
} | sort -u -k1,1 | sed "s#\t\t\t#\n#" > /manifest-owns.txt


du -akx --exclude=/var/cache/yum / > /manifest-file.txt
du -x --exclude=/var/cache/yum / > /manifest-dir.txt
echo -n "."
bzip2 /manifest-deps.txt /manifest-owns.txt /manifest-file.txt /manifest-dir.txt
echo -n "."

%end

%post --nochroot
# Move manifests to ISO
mv $INSTALL_ROOT/manifest-* $LIVE_ROOT/isolinux
echo "done"

# only works on x86, x86_64
if [ "$(uname -i)" = "i386" -o "$(uname -i)" = "x86_64" ]; then
    if [ ! -d $LIVE_ROOT/LiveOS ]; then mkdir -p $LIVE_ROOT/LiveOS ; fi
    cp /usr/bin/livecd-iso-to-disk $LIVE_ROOT/LiveOS
    cp /usr/bin/livecd-iso-to-pxeboot $LIVE_ROOT/LiveOS
fi
%end
