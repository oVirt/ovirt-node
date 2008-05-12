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

$: << File.join(File.dirname(__FILE__), "../dutils")

require 'rubygems'
require 'libvirt'
require 'optparse'
require 'daemons'
include Daemonize

$logfile = '/var/log/ovirt-wui/host-status.log'

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

# connects to the db in here
require 'dutils'

def check_state(vm, dom_info)
  case dom_info.state

  when Libvirt::Domain::NOSTATE, Libvirt::Domain::SHUTDOWN,
    Libvirt::Domain::SHUTOFF, Libvirt::Domain::CRASHED then
    if Vm::RUNNING_STATES.include?(vm.state)
      # OK, the host thinks this VM is off, while the database thinks it
      # is running; we have to kick taskomatic
      kick_taskomatic(Vm::STATE_STOPPED, vm)
    end
  when Libvirt::Domain::RUNNING, Libvirt::Domain::BLOCKED then
    if not Vm::RUNNING_STATES.include?(vm.state)
      # OK, the host thinks this VM is running, but it's not marked as running
      # in the database; kick taskomatic
      kick_taskomatic(Vm::STATE_RUNNING, vm)
    end
  when Libvirt::Domain::PAUSED then
    if vm.state != Vm::STATE_SUSPENDING and vm.state != Vm::STATE_SUSPENDED
      kick_taskomatic(Vm::STATE_SUSPENDED, vm)
    end
  else
    puts "Unknown vm state...skipping"
  end
end


def kick_taskomatic(msg, vm)
  print "Kicking taskomatic, state is %s\n" % msg
  task = VmTask.new
  task.user = "host-status"
  task.action = VmTask::ACTION_UPDATE_STATE_VM
  task.state = Task::STATE_QUEUED
  task.args = msg
  task.created_at = Time.now
  task.time_started = Time.now
  task.vm_id = vm.id
  task.save
end

loop do
  puts "Waking up to check host status"
  get_credentials

  hosts = Host.find(:all)
  hosts.each do |host|
    
    puts "checking host" + host.hostname

    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
    rescue
      # we couldn't contact the host for whatever reason.  Since we can't get to this
      # host, we have to mark all vms on it as disconnected or stopped or such.
      puts "Failed to contact host " + host.hostname + "; skipping for now", $!
      vms = Vm.find(:all, :conditions => [ "host_id = ?", host.id ])
      vms.each do |vm|
        # Since we can't reach the host on which the vms reside, we mark these as
        # STATE_UNREACHABLE.  If they come back up we can mark them as running again,
        # else they'll be stopped.  At least for now the user will know what's going on.
        #
        # If this causes too much trouble in the UI, this can be changed to STATE_STOPPED
        # for now until it is resolved of another solution is brought forward.
        kick_taskomatic(Vm::STATE_UNREACHABLE, vm)
      end

      next
    end

    begin
      vm_ids = conn.list_domains
    rescue
      puts "Failed to request domain list on host " + host.hostname
      conn.close
      next
    end

    puts vm_ids.length

    # Here we're going through every vm listed through libvirt.  This
    # really only lets us find ones that are started that shouldn't be.
    vm_ids.each do |vm_id|
      puts "VM ID: %d" % [vm_id]
      begin
        dom = conn.lookup_domain_by_id(vm_id)
      rescue
        puts "Failed to find domain " + vm.description
        next
      end
      
      vm_uuid = dom.uuid
      info = dom.info

      puts "VM UUID: %s" % [vm_uuid]
      info = dom.info
      puts info.to_s
 
      vm = Vm.find(:first, :conditions => [ "uuid = ?", vm_uuid ])
      if vm == nil
        puts "VM Not found in database, must be created by user.  giving up."
        next
      end

      check_state(vm, info)
    end

    # Now we get a list of all vms that should be on this system and see if
    # they are all running.
    vms = Vm.find(:all, :conditions => [ "host_id = ?", host.id ])
    vms.each do |vm|
    
      begin
        dom = conn.lookup_domain_by_uuid(vm.uuid)
      rescue
        # OK.  We couldn't find the UUID that we thought was there.  The only
        # explanation is that the domain is dead.
        puts "Failed to find domain " + vm.description
        kick_taskomatic(Vm::STATE_STOPPED, vm)
        next
      end
      info = dom.info
      check_state(vm, info)

      conn.close

    end
  end

  STDOUT.flush
  sleep sleeptime
end


