#!/bin/bash

# gettree.sh <Fedora release URL>
#   Fedora release URL - Fedora base URL
#     e.g. http://download.fedoraproject.org/pub/fedora/linux/releases/9/Fedora/x86_64/os
#   download minimal Fedora tree: .treeinfo stage2 initrd and kernel

download() {
    local f=$1
    wget --progress=dot:mega --continue $1
    printf "."
}

if [ -z "$1" ]; then
    cat >&2 << EOF
Usage: $(basename "$0") <Fedora release URL>
EOF
    exit 1
fi

url=$1
printf "Downloading minimal Fedora install tree from $url"
set -e
download $url/.treeinfo
mkdir -p images/pxeboot
cd images
download $url/images/stage2.img
cd pxeboot
download $url/images/pxeboot/initrd.img
download $url/images/pxeboot/vmlinuz
echo "done"
