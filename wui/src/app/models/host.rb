#
# Copyright (C) 2008 Red Hat, Inc.
# Written by Scott Seago <sseago@redhat.com>
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

require 'util/ovirt'

class Host < ActiveRecord::Base
  belongs_to :hardware_pool

  has_many :cpus, :dependent => :destroy
  has_many :nics, :dependent => :destroy
  has_many :vms,  :dependent => :nullify do

    def consuming_resources
      find(:all, :conditions=>{:state=>Vm::RUNNING_STATES})
    end
  end
  has_many :tasks, :class_name => "HostTask", :dependent => :destroy, :order => "id DESC" do
    def queued
      find(:all, :conditions=>{:state=>Task::STATE_QUEUED})
    end
    def pending_clear_tasks
      find(:all, :conditions=>{:state=>Task::WORKING_STATES,
                               :action=>HostTask::ACTION_CLEAR_VMS})
    end
  end

  acts_as_xapian :texts => [ :hostname, :uuid, :hypervisor_type, :arch ],
                 :values => [ [ :created_at, 0, "created_at", :date ],
                              [ :updated_at, 1, "updated_at", :date ] ],
                 :terms => [ [ :hostname, 'H', "hostname" ],
                             [ :search_users, 'U', "search_users" ] ]


  KVM_HYPERVISOR_TYPE = "KVM"
  HYPERVISOR_TYPES = [KVM_HYPERVISOR_TYPE]
  STATE_UNAVAILABLE = "unavailable"
  STATE_AVAILABLE   = "available"
  STATES = [STATE_UNAVAILABLE, STATE_AVAILABLE]

  def memory_in_mb
    kb_to_mb(memory)
  end

  def memory_in_mb=(mem)
    self[:memory]=(mb_to_kb(mem))
  end

  def status_str
    "#{state} (#{disabled? ? 'disabled':'enabled'})"
  end

  def disabled?
    not(is_disabled.nil? or is_disabled==0)
  end

  def is_clear_task_valid?
    state==STATE_AVAILABLE and
      not(disabled? and vms.consuming_resources.empty?) and
      tasks.pending_clear_tasks.empty?
  end

  def num_cpus
    return cpus.size
  end

  def cpu_speed
    "FIX ME!"
  end

  def display_name
    hostname
  end
  def display_class
    "Host"
  end

  def search_users
    hardware_pool.search_users
  end

end
