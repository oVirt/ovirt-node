%include common-install.ks

%include repos.ks

%packages --excludedocs --nobase
%include common-pkgs.ks

%end

%post
%include common-post.ks

%end
