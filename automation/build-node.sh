#!/bin/bash -xe
echo "build-node.sh"
#this scripts build ovirt-node and ovirt-node-is projects

# the die on error function
function die {
    echo "$1"
    exit 1
}


#sets the env variables required for the rest
export CACHE="$PWD"/build
export OVIRT_NODE_BASE="$PWD/.."
export OVIRT_CACHE_DIR="$CACHE"
export OVIRT_LOCAL_REPO=file://"$OVIRT_CACHE_DIR"/ovirt


for dir in exported-artifacts; do
    rm -Rf "$dir"
    mkdir -p "$dir"
done

rm -rf "$CACHE"
cd "$OVIRT_NODE_BASE"/ovirt-node
# get rid of old makefiles
 git clean -dfx
# generate new makefiles
./autogen.sh
make distclean || clean_failed=true

./autogen.sh --with-image-minimizer
if ! make publish ; then
    die "Node building failed"
fi
