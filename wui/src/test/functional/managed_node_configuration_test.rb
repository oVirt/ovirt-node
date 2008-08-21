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

require File.dirname(__FILE__) + '/../test_helper'
require 'test/unit'
require 'managed_node_configuration'

# Performs unit tests on the +ManagedNodeConfiguration+ class.
#
class ManagedNodeConfigurationTest < Test::Unit::TestCase
  def setup
    @host   = Host.new
    @nic    = Nic.new(:mac => '00:11:22:33:44:55')
    @host.nics << @nic
  end

  # Ensures that network interfaces uses DHCP when no IP address is specified.
  #
  def test_generate_with_no_ip_address
    expected = <<-HERE
rm /files/etc/sysconfig/network-scripts/ifcfg-eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/DEVICE eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/BOOTPROTO dhcp
    HERE

    result = ManagedNodeConfiguration.generate(
      @host,
      {'00:11:22:33:44:55' => 'eth0'}
    )

    assert_equal expected, result
  end

  # Ensures that network interfaces use the IP address when it's provided.
  #
  def test_generate_with_ip_address
    @nic.ip_addr = '192.168.2.1'

    expected = <<-HERE
rm /files/etc/sysconfig/network-scripts/ifcfg-eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/DEVICE eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/IPADDR 192.168.2.1
    HERE

    result = ManagedNodeConfiguration.generate(
      @host,
      {'00:11:22:33:44:55' => 'eth0'}
    )

    assert_equal expected, result
  end

  # Ensures the bridge is added to the configuration if one is defined.
  #
  def test_generate_with_bridge
    @nic.bridge = 'ovirtbr0'

    expected = <<-HERE
rm /files/etc/sysconfig/network-scripts/ifcfg-eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/DEVICE eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/BOOTPROTO dhcp
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/BRIDGE ovirtbr0
    HERE

    result = ManagedNodeConfiguration.generate(
      @host,
      {'00:11:22:33:44:55' => 'eth0'}
    )

    assert_equal expected, result
  end

  # Ensures that more than one NIC is successfully processed.
  #
  def test_generate_with_multiple_nics
    @host.nics << Nic.new(:mac => '11:22:33:44:55:66', :ip_addr => '172.31.0.15')
    @host.nics << Nic.new(:mac => '22:33:44:55:66:77', :ip_addr => '172.31.0.100')
    @host.nics << Nic.new(:mac => '33:44:55:66:77:88')


    expected = <<-HERE
rm /files/etc/sysconfig/network-scripts/ifcfg-eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/DEVICE eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/BOOTPROTO dhcp
rm /files/etc/sysconfig/network-scripts/ifcfg-eth1
set /files/etc/sysconfig/network-scripts/ifcfg-eth1/DEVICE eth1
set /files/etc/sysconfig/network-scripts/ifcfg-eth1/IPADDR 172.31.0.15
rm /files/etc/sysconfig/network-scripts/ifcfg-eth2
set /files/etc/sysconfig/network-scripts/ifcfg-eth2/DEVICE eth2
set /files/etc/sysconfig/network-scripts/ifcfg-eth2/IPADDR 172.31.0.100
rm /files/etc/sysconfig/network-scripts/ifcfg-eth3
set /files/etc/sysconfig/network-scripts/ifcfg-eth3/DEVICE eth3
set /files/etc/sysconfig/network-scripts/ifcfg-eth3/BOOTPROTO dhcp
    HERE

    result = ManagedNodeConfiguration.generate(
      @host,
      {
        '00:11:22:33:44:55' => 'eth0',
        '11:22:33:44:55:66' => 'eth1',
        '22:33:44:55:66:77' => 'eth2',
        '33:44:55:66:77:88' => 'eth3'
      })

    assert_equal expected, result
  end
end
