url --url http://download.fedora.redhat.com/pub/fedora/linux/releases/9/Fedora/x86_64/os/

repo --name=f9 --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-9&arch=$basearch
repo --name=f9-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f9&arch=$basearch
repo --name=ovirt --baseurl=http://ovirt.org/repos/ovirt/9/x86_64

