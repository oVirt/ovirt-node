#oVirt autobuild script
#
# Copyright (C) 2008 Red Hat, Inc.
# Written by Mohammed Morsi <mmorsi@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
die() { warn "$@"; exit 1; }

echo "Running oVirt Autobuild"

ssh_cmd="ssh -o StrictHostKeyChecking=no \
             -o UserKnownHostsFile=/dev/null root@192.168.50.2"

# implant local ssh key into appliance for autobuild only
if [ ! -r ~/.ssh/id_rsa.pub ]; then
  die "requires default SSH key to be generated. Please run ssh-keygen -t rsa"
fi
cat >> wui-appliance/common-post.ks << \KS
mkdir -p /root/.ssh
chmod 700 /root/.ssh
cat > /root/.ssh/authorized_keys << \EOF
KS
cat ~/.ssh/id_rsa.pub >> wui-appliance/common-post.ks
cat >> wui-appliance/common-post.ks << \KS
EOF
chmod 600 /root/.ssh/authorized_keys
KS
# move sshd to start last (after ovirt*first-run scripts)
cat >> wui-appliance/common-post.ks << \KS
mkdir -p /etc/chkconfig.d
cat > /etc/chkconfig.d/sshd << \EOF
# chkconfig: 2345 99 01
EOF
chkconfig --override sshd
KS

# create appliance
./build-all.sh -ac \
  || die "./build-all.sh failed, appliance not created"

# start appliance
virsh start ovirt-appliance

# wait until started
for i in $(seq 1 60); do
   $ssh_cmd exit && break
   sleep 10
done

echo "Running the wui tests"
$ssh_cmd \
    "curl -i --negotiate -u : management.priv.ovirt.org/ovirt/ | \
       grep 'HTTP/1.1 200 OK' && \
     cd /usr/share/ovirt-wui && rake test"
