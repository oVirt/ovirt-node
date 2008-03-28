all: ks

ks:
	ksflatten wui-app-i386.ks > wui-rel-app-i386.ks
	ksflatten wui-app-x86_64.ks > wui-rel-app-x86_64.ks
	ksflatten wui-devel-i386.ks > wui-rel-devel-i386.ks
	ksflatten wui-devel-x86_64.ks > wui-rel-devel-x86_64.ks

clean:
	rm -f *-rel-*
