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

%include common-blacklist.ks

%post --nochroot
%include common-post-nochroot.ks

%end

%include common-manifest-post.ks

