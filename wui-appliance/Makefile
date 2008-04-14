all: ks

primary_src = \
  wui-app-x86_64.ks	\
  wui-devel-x86_64.ks

rel_ks =		\
  wui-rel-app-i386.ks	\
  wui-rel-app-x86_64.ks	\
  wui-rel-devel-i386.ks	\
  wui-rel-devel-x86_64.ks

ks: $(rel_ks)

define ks-flatten
  rm -f $@ $@-t
  ksflatten $< > $@-t
  chmod a=r $@-t
  mv $@-t $@
endef

wui-rel-app-%.ks: wui-app-%.ks
	$(ks-flatten)

wui-rel-devel-%.ks: wui-devel-%.ks
	$(ks-flatten)

# Generate each wui-*-i386.ks file from the corresponding x86_64.ks one.
wui-%-i386.ks: wui-%-x86_64.ks
	rm -f $@ $@-t
	sed 's/x86_64/i386/' $< > $@-t
	chmod a=r $@-t
	mv $@-t $@

# Generate dependencies.
include .deps
.deps: $(primary_src)
	rm -f .deps
	for i in $^; do	\
	  sed -n '/^%include \(.*\.ks\)$$/s//'"$$i: "'\1/p' $$i >> $@-t; \
	done
	mv $@-t $@

clean:
	rm -f wui-devel-i386.ks wui-app-i386.ks $(rel_ks) .deps
