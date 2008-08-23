%include common-install.ks

%include repos.ks

%packages --excludedocs --nobase
%include common-pkgs.ks

%end

%post
%include common-post.ks

%end

%post --nochroot
# remove quiet from Node bootparams, added by livecd-creator
sed -i -e 's/ quiet//' $LIVE_ROOT/isolinux/isolinux.cfg

%end
