NAME=ovirt-appliance
YUMCACHE=$$(pwd)/../tmp/cache
F_REL := $(shell rpm -q --qf '%{VERSION}' fedora-release)
ARCH  := $(shell uname -i)

appliance: $(NAME)-sda.raw

appliance-compressed: $(NAME)-sda.qcow

$(NAME)-sda.raw: *.ks tmp/tree/.treeinfo
	mkdir -p tmp
	appliance-creator --config wui-devel.ks --name $(NAME) \
	  --tmpdir="$$(pwd)/tmp" --cache="$(YUMCACHE)"

$(NAME)-sda.qcow: $(NAME)-sda.raw
	# FIXME add --compress option to appliance-creator
	qemu-img convert -c $(NAME)-sda.raw -O qcow2 $(NAME)-sda.qcow

repos.ks: ../common/repos.ks.in
	cp ../common/repos.ks.in repos.ks

tmp/tree/.treeinfo:
	mkdir -p tmp/tree
	cd tmp/tree; ../../gettree.sh \
	  http://download.fedoraproject.org/pub/fedora/linux/releases/$(F_REL)/Fedora/$(ARCH)/os

clean:
	rm -f repos.ks

distclean: clean
	rm -rf $(NAME)-sda.raw $(NAME)-sda.qcow tmp

.PHONY: appliance appliance-compressed clean distclean
