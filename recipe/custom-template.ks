# oVirt Node image recipe
# This an example TEMPLATE for customizations.

%include common-install.ks
# add custom installation directives here

%include repos.ks
# add custom repos here

%packages --excludedocs --nobase
%include common-pkgs.ks
# add custom package list here

%end

%post
%include common-post.ks
# add custom post-scripts here

%end

%include common-blacklist.ks

%post --nochroot
%include common-post-nochroot.ks
# add custom post-scripts running outside image chroot here

%end

%include common-manifest-post.ks

