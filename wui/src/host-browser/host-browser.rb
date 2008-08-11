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

$: << File.join(File.dirname(__FILE__), "../dutils")
$: << File.join(File.dirname(__FILE__), "../")

require 'rubygems'
require 'libvirt'
require 'dutils'

require 'socket'
require 'krb5_auth'
include Krb5Auth
require 'daemons'
include Daemonize

include Socket::Constants

$logfile = '/var/log/ovirt-wui/host-browser.log'

# +HostBrowser+ communicates with the a managed node. It retrieves specific information
# about the node and then updates the list of active nodes for the WUI.
#
class HostBrowser
    attr_accessor :logfile
    attr_accessor :keytab_dir
    attr_accessor :keytab_filename

    def initialize(session)
        @session = session
        @log_prefix = "[#{session.peeraddr[3]}] "
        @keytab_dir = '/usr/share/ipa/html/'
    end

    # Ensures the conversation starts properly.
    #
    def begin_conversation
        puts "#{@log_prefix} Begin conversation" unless defined?(TESTING)
        @session.write("HELLO?\n")

        response = @session.readline.chomp
        raise Exception.new("received #{response}, expected HELLO!") unless response == "HELLO!"
    end

    # Retrieves the mode request from the remote system.
    #
    def get_mode
        puts "#{@log_prefix} Determining the runtime mode." unless defined?(TESTING)
        @session.write("MODE?\n")
        response = @session.readline.chomp
        puts "#{@log_prefix} MODE=#{response}" unless defined?(TESTING)

        response
    end

    # Requests node information from the remote system.
    #
    def get_remote_info
        puts "#{@log_prefix} Begin remote info collection" unless defined?(TESTING)
        result = Hash.new
        result['HOSTNAME'] = @session.peeraddr[2]
        result['IPADDR']   = @session.peeraddr[3]

        @session.write("INFO?\n")

        loop do
            info = @session.readline.chomp

            puts "Received info='#{info}'"

            break if info == "ENDINFO"

            case info
            when "CPU"
                cpu = get_cpu_info
                cpu_info = result['CPUINFO']

                if(cpu_info == nil)
                    cpu_info = Array.new
                    result['CPUINFO'] = cpu_info
                end

                cpu_info << cpu
            when "NIC"
                nic = get_nic_info
                nic_info = result['NICINFO']

                if(nic_info == nil)
                    nic_info = Array.new
                    result['NICINFO'] = nic_info
                end

                nic_info << nic
            else

                raise Exception.new("ERRINFO! Excepted key=value : #{info}\n") unless info =~ /[\w]+[\s]*=[\w]/

                key, value = info.split("=")

                puts "#{@log_prefix} ::Received - #{key}:#{value}" unless defined?(TESTING)
                result[key] = value

                @session.write("ACK #{key}\n")
            end
        end

        return result
    end

    # Extracts CPU details from the managed node.
    #
    def get_cpu_info
        puts "Begin receiving CPU details"

        result = Hash.new

        @session.write("CPUINFO?\n")

        loop do
            info = @session.readline.chomp

            break if info == "ENDCPU"

            raise Exception.new("ERRINFO! Excepted key=value : #{info}\n") unless info =~ /[\w]+[\s]*=[\w]/

            key, value = info.split("=")

            puts "#{@log_prefix} ::Received - #{key}:#{value}" unless defined?(TESTING)
            result[key] = value

            @session.write("ACK #{key}\n")
        end

        @session.write("ACK CPU\n");

        return result
    end

    # Extracts NIC details from the managed node.
    #
    def get_nic_info
        puts "Begin receiving NIC details"

        result = Hash.new

        @session.write("NICINFO?\n")

        loop do
            info = @session.readline.chomp

            break if info == "ENDNIC"

            raise Exception.new("ERRINFO! Excepted key=value : #{info}\n") unless info =~ /[\w]+[\s]*=[\w]/

            key, value = info.split("=")

            puts "#{@log_prefix} ::Received - #{key}:#{value}" unless defined?(TESTING)
            result[key] = value

            @session.write("ACK #{key}\n")
        end

        @session.write("ACK NIC\n");

        return result
    end

    # Writes the supplied host information to the database.
    #
    def write_host_info(host_info)
        ensure_present(host_info,'HOSTNAME')
        ensure_present(host_info,'ARCH')
        ensure_present(host_info,'MEMSIZE')
        ensure_present(host_info,'CPUINFO')
        ensure_present(host_info,'NICINFO')

        cpu_info = host_info['CPUINFO']
        nic_info = host_info['NICINFO']

        cpu_info.each do |cpu|
            ensure_present(cpu,'CPUNUM')
            ensure_present(cpu,'CORENUM')
            ensure_present(cpu,'NUMCORES')
            ensure_present(cpu,'VENDOR')
            ensure_present(cpu,'MODEL')
            ensure_present(cpu,'FAMILY')
            ensure_present(cpu,'CPUIDLVL')
            ensure_present(cpu,'SPEED')
            ensure_present(cpu,'CACHE')
            ensure_present(cpu,'FLAGS')
        end

        puts "Searching for existing host record..." unless defined?(TESTING)
        host = Host.find(:first, :conditions => ["hostname = ?", host_info['HOSTNAME']])

        if host == nil
            begin
                puts "Creating a new record for #{host_info['HOSTNAME']}..." unless defined?(TESTING)

                host = Host.create(
                    "uuid"            => host_info['UUID'],
                    "hostname"        => host_info['HOSTNAME'],
                    "hypervisor_type" => host_info['HYPERVISOR_TYPE'],
                    "arch"            => host_info['ARCH'],
                    "memory"          => host_info['MEMSIZE'],
                    "is_disabled"     => 0,
                    "hardware_pool"   => HardwarePool.get_default_pool,
                    # Let host-status mark it available when it
                    # successfully connects to it via libvirt.
                    "state"           => Host::STATE_UNAVAILABLE)
            rescue Exception => error
                puts "Error while creating record: #{error.message}" unless defined?(TESTING)
            end
        else
            host.uuid         = host_info['UUID']
            host.hostname     = host_info['HOSTNAME']
            host.arch         = host_info['ARCH']
            host.memory       = host_info['MEMSIZE']
        end

        # delete an existing CPUs and create new ones based on the data
        puts "Deleting any existing CPUs"
        Cpu.delete_all(['host_id = ?', host.id])

        puts "Saving new CPU records"
        cpu_info.collect do |cpu|
            detail = Cpu.new(
                "cpu_number"      => cpu['CPUNUM'],
                "core_number"     => cpu['CORENUM]'],
                "number_of_cores" => cpu['NUMCORES'],
                "vendor"          => cpu['VENDOR'],
                "model"           => cpu['MODEL'],
                "family"          => cpu['FAMILY'],
                "cpuid_level"     => cpu['CPUIDLVL'],
                "speed"           => cpu['SPEED'],
                "cache"           => cpu['CACHE'],
                "flags"           => cpu['FLAGS'])

            host.cpus << detail
         end

        # Update the NIC details for this host:
        # -if the NIC exists, then update the IP address
        # -if the NIC does not exist, create it
        # -any nic not in this list is deleted

        puts "Updating NIC records for the node"
        nics = Array.new

        host.nics.collect do |nic|
            found = false

            nic_info.collect do |detail|
                # if we have a match, then update the database and remove
                # the received data to avoid creating a dupe later
                if detail['MAC'] == nic.mac
                    nic_info.delete(detail)
                end
            end

            # if the record wasn't found, then remove it from the database
            unless found
                host.nics.delete(nic)
                nic.destroy
            end
        end

        # iterate over any nics left and create new records for them.

        nic_info.collect do |nic|
            puts "Creating a new nic..."
            detail = Nic.new(
                'mac'        => nic['MAC'],
                'bandwidth'  => nic['BANDWIDTH'],
                'usage_type' => 1)

            host.nics << detail
        end

        host.save!

        return host
    end

    # Creates a keytab if one is needed, returning the filename.
    #
    def create_keytab(hostname, ipaddress, krb5_arg = nil)
        krb5 = krb5_arg || Krb5.new

        default_realm = krb5.get_default_realm
        libvirt_princ = 'libvirt/' + hostname + '@' + default_realm
        outfile = ipaddress + '-libvirt.tab'
        @keytab_filename = @keytab_dir + outfile

        # TODO need a way to test this portion
        unless (defined? TESTING) || File.exists?(@keytab_filename)
            # TODO replace with Kr5Auth when it supports admin actions
            puts "Writing keytab file: #{@keytab_filename}" unless defined?(TESTING)
            kadmin_local('addprinc -randkey ' + libvirt_princ)
            kadmin_local('ktadd -k ' + @keytab_filename + ' ' + libvirt_princ)

            File.chmod(0644,@keytab_filename)
        end

        hostname = `hostname -f`.chomp

        @session.write("KTAB http://#{hostname}/ipa/config/#{outfile}\n")

        response = @session.readline.chomp

        raise Exception.new("ERRINFO! No keytab acknowledgement") unless response == "ACK"
    end

    # Ends the conversation, notifying the user of the key version number.
    #
    def end_conversation
        puts "#{@log_prefix} Ending conversation" unless defined?(TESTING)

        @session.write("BYE\n");
    end

    private

    # Private method to ensure that a required field is present.
    #
    def ensure_present(info,key)
        raise Exception.new("ERROR! Missing '#{key}'...") if info[key] == nil
    end

    # Executes an external program to support the keytab function.
    #
    def kadmin_local(command)
        system("/usr/kerberos/sbin/kadmin.local -q '" + command + "'")
    end
end

def entry_point(server)
    while(session = server.accept)
        child = fork do
            remote = session.peeraddr[2]

            puts "Connected to #{remote}" unless defined?(TESTING)

            # This is needed because we just forked a new process
            # which now needs its own connection to the database.
            database_connect

            begin
                browser = HostBrowser.new(session)

                browser.begin_conversation
                case browser.get_mode
                    when "AWAKEN": browser.create_keytab(remote,session.peeraddr[3])
                    when "IDENTIFY": browser.write_host_info(browser.get_remote_info)
                end

                browser.end_conversation
            rescue Exception => error
                session.write("ERROR #{error.message}\n")
                puts "ERROR #{error.message}" unless defined?(TESTING)
            end

            puts "Disconnected from #{remote}" unless defined?(TESTING)
        end

        Process.detach(child)
    end
end

unless defined?(TESTING)
    # The main entry point.
    #
    unless ARGV[0] == "-n"
        daemonize
        # redirect output to the log
        STDOUT.reopen $logfile, 'a'
        STDERR.reopen STDOUT
    end

    server = TCPServer.new("",12120)
    entry_point(server)
end
