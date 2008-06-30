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
        @host_info['ARCH']     = 'x86_64'
        @host_info['MEMSIZE']  = '16384'
        @host_info['DISABLED'] = '0'

        @host_info['NUMCPUS']  = '2'

        @host_info['CPUINFO'] = Array.new
        @host_info['CPUINFO'][0] = {}
        @host_info['CPUINFO'][0]['CPUNUM']   = '0'
        @host_info['CPUINFO'][0]['CORENUM']  = '0'
        @host_info['CPUINFO'][0]['NUMCORES'] = '2'
        @host_info['CPUINFO'][0]['VENDOR']   = 'GenuineIntel'
        @host_info['CPUINFO'][0]['MODEL']    = '15'
        @host_info['CPUINFO'][0]['FAMILY']   = '6'
        @host_info['CPUINFO'][0]['CPUIDLVL'] = '10'
        @host_info['CPUINFO'][0]['SPEED']    = '3'
        @host_info['CPUINFO'][0]['CACHE']    = '4096 kb'
        @host_info['CPUINFO'][0]['FLAGS']    = 'fpu vme de pse tsc msr pae \
            mce cx8 apic mtrr pge mca cmov pat pse36 clflush dts acpi mmx \
            fxsr sse sse2 ss ht tm pbe nx lm constant_tsc arch_perfmon pebs \
            bts pni monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr lahf_lm'

        @host_info['CPUINFO'][1] = {}
        @host_info['CPUINFO'][1]['CPUNUM']   = '1'
        @host_info['CPUINFO'][1]['CORENUM']  = '1'
        @host_info['CPUINFO'][1]['NUMCORES'] = '2'
        @host_info['CPUINFO'][1]['VENDOR']   = 'GenuineIntel'
        @host_info['CPUINFO'][1]['MODEL']    = '15'
        @host_info['CPUINFO'][1]['FAMILY']   = '6'
        @host_info['CPUINFO'][1]['CPUIDLVL'] = '10'
        @host_info['CPUINFO'][1]['SPEED']    = '3'
        @host_info['CPUINFO'][1]['CACHE']    = '4096 kb'
        @host_info['CPUINFO'][1]['FLAGS']    = 'fpu vme de pse tsc msr pae \
            mce cx8 apic mtrr pge mca cmov pat pse36 clflush dts acpi mmx \
            fxsr sse sse2 ss ht tm pbe nx lm constant_tsc arch_perfmon pebs \
            bts pni monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr lahf_lm'
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

        assert_equal 4,info.keys.size, "Should contain four keys"
        assert info.include?("IPADDR")
        assert info.include?("HOSTNAME")
        assert info.include?("key1")
        assert info.include?("key2")
    end

    # Ensures that the server is fine when no UUID is present.
    #
    def test_write_host_info_with_missing_uuid
        @host_info['UUID'] = nil

        assert_nothing_raised { @browser.write_host_info(@host_info) }
    end

    # Ensures that, if the hostname is missing, the server
    # raises an exception.
    #
    def test_write_host_info_with_missing_hostname
        @host_info['HOSTNAME'] = nil

        assert_raise(Exception) { @browser.write_host_info(@host_info) }
    end

    # Ensures that, if the architecture is missing, the server raises an
    # exception.
    #
    def test_write_host_info_with_missing_arch
        @host_info['ARCH'] = nil

        assert_raise(Exception) { @browser.write_host_info(@host_info) }
    end

    # Ensures that, if the memory size is missing, the server raises an
    # exception.
    #
    def test_write_host_info_info_with_missing_memsize
        @host_info['MEMSIZE'] = nil

        assert_raise(Exception) { @browser.write_host_info(@host_info) }
    end

    # Ensures that, if no cpu info was available, the server raises an
    # exception.
    #
    def test_write_host_info_with_missing_cpuinfo
        @host_info['CPUINFO'] = nil

        assert_raise(Exception) { @browser.write_host_info(@host_info) }
    end

    # Ensures the browser can properly parse the CPU details.
    #
    def test_parse_cpu_info
        @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "CPU\n" }
        @session.should_receive(:write).with("CPUINFO?\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "key1=value1\n" }
        @session.should_receive(:write).with("ACK key1\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "key2=value2\n" }
        @session.should_receive(:write).with("ACK key2\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "ENDCPU\n" }
        @session.should_receive(:write).with("ACK CPU\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "ENDINFO\n" }

        info = @browser.get_remote_info

        assert_equal 3,info.keys.size, "Should contain four keys"
        assert info.include?("CPUINFO")
    end

    # Ensures the browser can properly parse the CPU details of two CPUs.
    #
    def test_parse_cpu_info
        @session.should_receive(:write).with("INFO?\n").once().returns { |request| request.length }

        # CPU 0
        @session.should_receive(:readline).once().returns { "CPU\n" }
        @session.should_receive(:write).with("CPUINFO?\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "key1=value1\n" }
        @session.should_receive(:write).with("ACK key1\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "key2=value2\n" }
        @session.should_receive(:write).with("ACK key2\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "ENDCPU\n" }
        @session.should_receive(:write).with("ACK CPU\n").once().returns { |request| request.length }

        # CPU 1
        @session.should_receive(:readline).once().returns { "CPU\n" }
        @session.should_receive(:write).with("CPUINFO?\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "key3=value3\n" }
        @session.should_receive(:write).with("ACK key3\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "key4=value4\n" }
        @session.should_receive(:write).with("ACK key4\n").once().returns { |request| request.length }
        @session.should_receive(:readline).once().returns { "ENDCPU\n" }
        @session.should_receive(:write).with("ACK CPU\n").once().returns { |request| request.length }

        @session.should_receive(:readline).once().returns { "ENDINFO\n" }

        info = @browser.get_remote_info

        assert_equal 3,info.keys.size, "Should contain four keys"
        assert info.include?('CPUINFO')
        assert_equal 2, info['CPUINFO'].size, "Should contain details for two CPUs"
        assert_not_nil info['CPUINFO'][0]['key1']
        assert_not_nil info['CPUINFO'][0]['key2']
        assert_not_nil info['CPUINFO'][1]['key3']
        assert_not_nil info['CPUINFO'][1]['key4']
    end

end
