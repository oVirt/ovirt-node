#!/usr/bin/ruby -Wall
#
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
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

require File.dirname(__FILE__) + '/../test/test_helper'
require 'test/unit'
require 'flexmock/test_unit'

TESTING=true

require 'host-browser'

class TestHostBrowser < Test::Unit::TestCase

  def setup
    @session = flexmock('session')
    @session.should_receive(:peeraddr).at_least.once.returns { [nil,nil,nil,"192.168.2.255"] }

    @browser = HostBrowser.new(@session)
    @browser.logfile = './unit-test.log'

    # default host info
    @host_info = {}
    @host_info['UUID']     = 'node1'
    @host_info['IPADDR']   = '192.168.2.2'
    @host_info['HOSTNAME'] = 'node1.ovirt.redhat.com'
    @host_info['NUMCPUS']  = '3'
    @host_info['CPUSPEED'] = '3'
    @host_info['ARCH']     = 'x86_64'
    @host_info['MEMSIZE']  = '16384'
    @host_info['DISABLED'] = '0'
  end

  # Ensures that the server is satisfied if the remote system is
  # making a wakeup call.
  #
  def test_get_mode_with_awaken_request
    @session.should_receive(:write).with("MODE?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "IDENTIFY\n" }

    result = @browser.get_mode()

    assert_equal "IDENTIFY", result, "method did not return the right value"
  end

  # Ensures that, if an info field is missing a key, the server raises
  # an exception.
  #
  def test_get_info_with_missing_key
    @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "=value1\n" }

    assert_raise(Exception) { @browser.get_remote_info }
  end

  # Ensures that, if an info field is missing a value, the server raises
  # an exception.
  #
  def test_get_info_with_missing_value
    @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "key1=\n" }

    assert_raise(Exception) { @browser.get_remote_info }
  end

  # Ensures that, if the server gets a poorly formed ending statement, it
  # raises an exception.
  #
  def test_get_info_with_invalid_end
    @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "key1=value1\n" }
    @session.should_receive(:write).with("ACK key1\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "ENDIFNO\n" }

    assert_raise(Exception) { @browser.get_remote_info }
  end

  # Ensures that a well-formed transaction works as expected.
  #
  def test_get_info
    @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "key1=value1\n" }
    @session.should_receive(:write).with("ACK key1\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "key2=value2\n" }
    @session.should_receive(:write).with("ACK key2\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "ENDINFO\n" }

    info = @browser.get_remote_info

    assert_equal 4,info.keys.size, "Should contain two keys"
    assert info.include?("IPADDR")
    assert info.include?("HOSTNAME")
    assert info.include?("key1")
    assert info.include?("key2")
  end

  # Ensures that, if no UUID is present, the server raises an exception.
  #
  def test_write_host_info_with_missing_uuid
    @host_info['UUID'] = nil

    assert_raise(Exception) { @browser.write_host_info(@host_info) }
  end

  # Ensures that, if the hostname is missing, the server
  # raises an exception.
  #
  def test_write_host_info_with_missing_hostname
    @host_info['HOSTNAME'] = nil

    assert_raise(Exception) { @browser.write_host_info(@host_info) }
  end

  # Ensures that, if the number of CPUs is missing, the server raises an exception.
  #
  def test_write_host_info_with_missing_numcpus
    @host_info['NUMCPUS'] = nil

    assert_raise(Exception) { @browser.write_host_info(@host_info) }
  end

  # Ensures that, if the CPU speed is missing, the server raises an exception.
  #
  def test_write_host_info_with_missing_cpuspeed
    @host_info['CPUSPEED'] = nil

    assert_raise(Exception) { @browser.write_host_info(@host_info) }
  end

  # Ensures that, if the architecture is missing, the server raises an exception.
  #
  def test_write_host_info_with_missing_arch
    @host_info['ARCH'] = nil

    assert_raise(Exception) { @browser.write_host_info(@host_info) }
  end

  # Ensures that, if the memory size is missing, the server raises an exception.
  #
  def test_write_host_info_info_with_missing_memsize
    @host_info['MEMSIZE'] = nil

    assert_raise(Exception) { @browser.write_host_info(@host_info) }
  end

end
