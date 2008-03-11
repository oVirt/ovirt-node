all: ks

ks:
	./ks_fold_include.py wui-app-i386.ks > wui-rel-app-i386.ks
	./ks_fold_include.py wui-app-x86_64.ks > wui-rel-app-x86_64.ks
	./ks_fold_include.py wui-devel-i386.ks > wui-rel-devel-i386.ks
	./ks_fold_include.py wui-devel-x86_64.ks > wui-rel-devel-x86_64.ks

clean:
	rm -f *-rel-*
