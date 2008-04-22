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
require 'optparse'

$logfile = '/var/log/ovirt-wui/taskomatic.log'

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

require 'dutils'
require 'task_vm'
require 'task_storage'

loop do
  puts 'Checking for tasks...'
  
  first = true
  Task.find(:all, :conditions => [ "state = ?", Task::STATE_QUEUED ]).each do |task|
    if first
      # make sure we get our credentials up-front
      get_credentials
      first = false
    end

    case task.action
    when VmTask::ACTION_CREATE_VM then create_vm(task)
    when VmTask::ACTION_SHUTDOWN_VM then shutdown_vm(task)
    when VmTask::ACTION_START_VM then start_vm(task)
    when VmTask::ACTION_SUSPEND_VM then suspend_vm(task)
    when VmTask::ACTION_RESUME_VM then resume_vm(task)
    when VmTask::ACTION_SAVE_VM then save_vm(task)
    when VmTask::ACTION_RESTORE_VM then restore_vm(task)
    when VmTask::ACTION_UPDATE_STATE_VM then update_state_vm(task)
    when StorageTask::ACTION_REFRESH_POOL then refresh_pool(task)
    else
      puts "unknown task " + task.action
      setTaskState(task, Task::STATE_FAILED, "Unknown task type")
    end
    
    task.time_ended = Time.now
    task.save
  end
  
  # we could destroy credentials, but another process might be using them (in
  # particular, host-browser).  Just leave them around, it shouldn't hurt
  
  STDOUT.flush
  sleep sleeptime
end
