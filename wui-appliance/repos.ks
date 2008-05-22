url --url http://download.fedora.redhat.com/pub/fedora/linux/releases/9/Fedora/x86_64/os/

repo --name=f9 --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-9&arch=x86_64
repo --name=f9-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f9&arch=x86_64
repo --name=ovirt --baseurl=http://ovirt.org/repos/ovirt/9/x86_64
# temporary
repo --name=f9testing --includepkgs=rubygem-rubyforge,rubygem-activeldap,rubygem-hoe --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-testing-f9&arch=x86_64

