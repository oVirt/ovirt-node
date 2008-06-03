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

    @krb5 = flexmock('krb5')

    @browser = HostBrowser.new(@session)
    @browser.logfile = './unit-test.log'
    @browser.keytab_dir = '/var/temp/'

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

  # Ensures that the server raises an exception when it receives an
  # improper handshake response.
  #
  def test_begin_conversation_with_improper_response_to_greeting
    @session.should_receive(:write).with("HELLO?\n").once().returns { |greeting| greeting.length }
    @session.should_receive(:readline).once().returns { "SUP?" }

    assert_raise(Exception) { @browser.begin_conversation }
  end

  # Ensures the server accepts a proper response from the remote system.
  #
  def test_begin_conversation
    @session.should_receive(:write).with("HELLO?\n").once().returns { |greeting| greeting.length }
    @session.should_receive(:readline).once().returns { "HELLO!\n" }

    assert_nothing_raised(Exception) { @browser.begin_conversation }
  end

  # Ensures that the server raises an exception when it receives
  # poorly formed data while exchanging system information.
  #
  def test_get_info_with_bad_handshake
    @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "key1=value1\n" }
    @session.should_receive(:write).with("ACK key1\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "farkledina\n" }

    assert_raise(Exception) { @browser.get_remote_info }
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

    assert_equal 3,info.keys.size, "Should contain two keys"
    assert info.include?("IPADDR")
    assert info.include?("key1")
    assert info.include?("key2")
  end

  # Ensures the host browser generates a keytab as expected.
  #
  def test_create_keytab
    @krb5.should_receive(:get_default_realm).once().returns { "ovirt-test-realm" }

    result = @browser.create_keytab(@host_info,@krb5)

    assert_equal @browser.keytab_filename, result, "Should have returned the keytab filename"
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

  # Ensures that, if a keytab is present and a key version number available,
  # the server ends the conversation by returning the key version number.
  #
  def test_end_conversation
    @session.should_receive(:write).with("KTAB 12345\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "ACK\n" }
    @session.should_receive(:write).with("BYE\n").once().returns { |request| request.length }

    assert_nothing_raised(Exception) { @browser.end_conversation(12345) }
  end

end
