# oVirt Node image recipe

%include common-install.ks

%include repos.ks

%packages --excludedocs --nobase
%include common-pkgs.ks

%end

%post
%include common-post.ks
%include common-el6.ks
%end

%post --nochroot
%include common-post-nochroot.ks

%end

%include common-initrd-post.ks
%include common-blacklist.ks
%include common-manifest-post.ks

