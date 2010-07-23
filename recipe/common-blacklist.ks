%post --nochroot --interpreter image-minimizer
%include common-minimizer.ks
%end

%post
echo "Removing python source files"
find / -name '*.py' -exec rm -f {} \;
find / -name '*.pyo' -exec rm -f {} \;

%end

