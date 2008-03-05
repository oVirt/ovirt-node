#!/usr/bin/ruby
# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Chris Lalancette <clalance@redhat.com>
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

$: << File.join(File.dirname(__FILE__), "../app")
$: << File.join(File.dirname(__FILE__), "../dutils")

require 'rubygems'
require 'active_record'
require 'libvirt'
require 'optparse'

require 'dutils'
require 'models/vm'
require 'models/host'

$logfile = '/var/log/ovirt-wui/host-status.log'

UPDATE_VM_OFF = 0
UPDATE_VM_RUNNING = 1
UPDATE_VM_PAUSHED = 2

def findHost(vm)
  host = Host.find(:first, :conditions => [ "id = ?", vm.host_id])

  if host == nil
    # Hm, we didn't find the host_id.  Seems odd.  Return a failure
    raise
  end

  return host
end

def kick_taskomatic(msg, vm)
  puts msg
end

do_daemon = true
sleeptime = 5
opts = OptionParser.new do |opts|
  opts.on("-h", "--help", "Print help message") do
    puts opts
    exit
  end
  opts.on("-n", "--nodaemon", "Run interactively (useful for debugging)") do |n|
    do_daemon = !n
  end
  opts.on("-s N", Integer, "--sleep", "Seconds to sleep between iterations (default is 5 seconds)") do |s|
    sleeptime = s
  end
end
begin
  opts.parse!(ARGV)
rescue OptionParser::InvalidOption
  puts opts
  exit
end

if do_daemon
  daemonize
  STDOUT.reopen $logfile, 'a'
  STDERR.reopen STDOUT
end

database_connect

loop do
  puts "hello"
  get_credentials
  vms = Vm.find(:all, :conditions => [ "host_id is NOT NULL" ])
  vms.each do |vm|
    host = findHost(vm)

    conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
    begin
      dom = conn.lookup_domain_by_uuid(vm.uuid)
    rescue
      # OK.  We couldn't find the UUID that we thought was there.  The only
      # explanation is that the domain is no longer there.  Kick taskomatic
      # and tell it
      kick_taskomatic(UPDATE_VM_OFF, vm)
      conn.close
      next
    end
    info = dom.info
    conn.close


    case info.state
    when Libvirt::Domain::NOSTATE, Libvirt::Domain::SHUTDOWN,
      Libvirt::Domain::SHUTOFF, Libvirt::Domain::CRASHED then
      if Vm::RUNNING_STATES.include?(vm.state)
        # OK, the host thinks this VM is off, while the database thinks it
        # is running; we have to kick taskomatic
        kick_taskomatic(UPDATE_VM_OFF, vm)
      end
    when Libvirt::Domain::RUNNING, Libvirt::Domain::BLOCKED then
      if not Vm::RUNNING_STATES.include?(vm.state)
        # OK, the host thinks this VM is running, but it's not marked as running
        # in the database; kick taskomatic
        kick_taskomatic(UPDATE_VM_RUNNING, vm)
      end
    when Libvirt::Domain::PAUSED then
      if vm.state != Vm::STATE_SUSPENDING and vm.state != Vm::STATE_SUSPENDED
        kick_taskomatic(UPDATE_VM_PAUSED, vm)
      end
    else
      puts "Unknown vm state...skipping"
    end
  end

  sleep sleeptime
end
