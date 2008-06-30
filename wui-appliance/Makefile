all: ks

ARCH		:= $(shell uname -i)

ks: wui-rel.ks

define ks-flatten
  rm -f $@ $@-t
  ksflatten $< > $@-t
  chmod a=r $@-t
  mv $@-t $@
endef

wui-rel.ks: wui-devel.ks repos.ks
	$(ks-flatten)

repos.ks: repos.ks.in
	sed "s/@@ARCH@@/$(ARCH)/" repos.ks.in > repos.ks

clean:
	rm -f repos.ks wui-rel.ks *~
