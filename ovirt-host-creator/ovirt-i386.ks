%include common-install.ks

%include repos.ks

%packages --excludedocs
%include common-pkgs.ks

%post
%include common-post.ks

%end
