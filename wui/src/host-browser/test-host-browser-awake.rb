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

# +TestHostBrowserAwaken+
class TestHostBrowserAwaken < Test::Unit::TestCase

  def setup
    @session = flexmock('session')
    @session.should_receive(:peeraddr).at_least.once.returns { [nil,nil,nil,"192.168.2.255"] }

    @krb5 = flexmock('krb5')

    @browser = HostBrowser.new(@session)
    @browser.logfile = './unit-test.log'
    @browser.keytab_dir = '/var/temp/'
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

  # Ensures that the server is satisfied if the remote system is
  # making a wakeup call.
  #
  def test_get_mode_with_awaken_request
    @session.should_receive(:write).with("MODE?\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "AWAKEN\n" }

    result = @browser.get_mode()

    assert_equal "AWAKEN", result, "method did not return the right value"
  end

  # Ensures the host browser generates a keytab as expected.
  #
  def test_create_keytab
    @krb5.should_receive(:get_default_realm).once().returns { "ovirt-test-realm" }
    servername = `hostname -f`.chomp
    @session.should_receive(:write).with("KTAB http://#{servername}/ipa/config/127.0.0.1-libvirt.tab\n").once().returns { |request| request.length }
    @session.should_receive(:readline).once().returns { "ACK\n" }

    assert_nothing_raised(Exception) { @browser.create_keytab('localhost','127.0.0.1',@krb5) }
  end

  # Ensures that, if a keytab is present and a key version number available,
  # the server ends the conversation by returning the key version number.
  #
  def test_end_conversation
    @session.should_receive(:write).with("BYE\n").once().returns { |request| request.length }

    assert_nothing_raised(Exception) { @browser.end_conversation }
  end

end
