all: ks

primary_src = \
  wui-devel-x86_64.ks \
  wui-devel-i386.ks

rel_ks =		\
  wui-rel-i386.ks	\
  wui-rel-x86_64.ks

ks: $(rel_ks)

define ks-flatten
  rm -f $@ $@-t
  ksflatten $< > $@-t
  chmod a=r $@-t
  mv $@-t $@
endef

wui-rel-%.ks: wui-devel-%.ks
	$(ks-flatten)

# Generate each *-i386.ks file from the corresponding -x86_64.ks one.
%-i386.ks: %-x86_64.ks
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
	rm -f wui-devel-i386.ks repos-i386.ks $(rel_ks) .deps *~
