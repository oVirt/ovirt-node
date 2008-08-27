#
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>.
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

# +ManagedNodeConfiguration+ takes in the description for a managed node and,
# from that, generates the configuration file that is consumed the next time
# the managed node starts up.
#

require 'stringio'

class ManagedNodeConfiguration
  NIC_ENTRY_PREFIX='/files/etc/sysconfig/network-scripts'

  def self.generate(host, macs)
    result = StringIO.new

    host.nics.each do |nic|
      iface_name = macs[nic.mac]

      if iface_name
        result.puts "rm #{NIC_ENTRY_PREFIX}/ifcfg-#{iface_name}"
        result.puts "set #{NIC_ENTRY_PREFIX}/ifcfg-#{iface_name}/DEVICE #{iface_name}"
        result.puts "set #{NIC_ENTRY_PREFIX}/ifcfg-#{iface_name}/IPADDR #{nic.ip_addr}"    if nic.ip_addr
        result.puts "set #{NIC_ENTRY_PREFIX}/ifcfg-#{iface_name}/BOOTPROTO dhcp"           if nic.ip_addr == nil
        result.puts "set #{NIC_ENTRY_PREFIX}/ifcfg-#{iface_name}/BRIDGE #{nic.bridge}"     if nic.bridge
      end
    end

    result.string
  end
end
