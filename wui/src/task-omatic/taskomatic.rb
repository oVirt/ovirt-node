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
$: << File.join(File.dirname(__FILE__), ".")

require 'rubygems'
require 'optparse'
require 'daemons'
include Daemonize

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

begin
  require 'dutils'
rescue => ex
  puts "dutils require failed! #{ex.class}: #{ex.message}"
end

require 'task_vm'
require 'task_storage'
require 'task_host'

loop do
  tasks = Array.new
  begin
    tasks = Task.find(:all, :conditions => [ "state = ?", Task::STATE_QUEUED ])
  rescue => ex
    puts "1 #{ex.class}: #{ex.message}"
    if Task.connected?
      begin
        ActiveRecord::Base.connection.reconnect!
      rescue => norecon
        puts "2 #{norecon.class}: #{norecon.message}"
      end
    else
      begin
        database_connect
      rescue => ex
        puts "3 #{ex.class}: #{ex.message}"
      end
    end
  end
  tasks.each do |task|
    # make sure we get our credentials up-front
    get_credentials

    task.time_started = Time.now

    state = Task::STATE_FINISHED
    begin
      case task.action
      when VmTask::ACTION_CREATE_VM then create_vm(task)
      when VmTask::ACTION_SHUTDOWN_VM then shutdown_vm(task)
      when VmTask::ACTION_START_VM then start_vm(task)
      when VmTask::ACTION_SUSPEND_VM then suspend_vm(task)
      when VmTask::ACTION_RESUME_VM then resume_vm(task)
      when VmTask::ACTION_SAVE_VM then save_vm(task)
      when VmTask::ACTION_RESTORE_VM then restore_vm(task)
      when VmTask::ACTION_UPDATE_STATE_VM then update_state_vm(task)
      when VmTask::ACTION_MIGRATE_VM then migrate_vm(task)
      when StorageTask::ACTION_REFRESH_POOL then refresh_pool(task)
      when HostTask::ACTION_CLEAR_VMS then clear_vms_host(task)
      else
        puts "unknown task " + task.action
        state = Task::STATE_FAILED
        task.message = "Unknown task type"
      end
    rescue => ex
      puts "Task action processing failed: #{ex.class}: #{ex.message}"
      puts ex.backtrace
      state = Task::STATE_FAILED
      task.message = ex.message
    end

    task.state = state
    task.time_ended = Time.now
    task.save
  end
  
  # we could destroy credentials, but another process might be using them (in
  # particular, host-browser).  Just leave them around, it shouldn't hurt
  
  STDOUT.flush
  sleep sleeptime
end
