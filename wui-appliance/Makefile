NAME=ovirt-appliance
YUMCACHE=$$(pwd)/../tmp/cache

appliance: $(NAME)-sda.raw

appliance-compressed: $(NAME)-sda.qcow

$(NAME)-sda.raw: wui-devel.ks common-install.ks common-pkgs.ks common-post.ks repos.ks
	appliance-creator --config wui-devel.ks --name $(NAME) \
	  --tmpdir=$$(pwd)/tmp --cache=$(YUMCACHE)

$(NAME)-sda.qcow: $(NAME)-sda.raw
	# FIXME add --compress option to appliance-creator
	qemu-img convert -c $(NAME)-sda.raw -O qcow2 $(NAME)-sda.qcow

repos.ks: repos.ks.in
	cp repos.ks.in repos.ks

clean:
	rm -f repos.ks

distclean: clean
	rm -rf $(NAME)-sda.raw $(NAME)-sda.qcow

.PHONY: appliance appliance-compressed clean distclean
