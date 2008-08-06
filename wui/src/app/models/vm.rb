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

class Vm < ActiveRecord::Base
  belongs_to :vm_resource_pool
  belongs_to :host
  has_many :tasks, :class_name => "VmTask", :dependent => :destroy, :order => "id ASC" do
    def queued
      find(:all, :conditions=>{:state=>Task::STATE_QUEUED})
    end
  end
  has_and_belongs_to_many :storage_volumes
  validates_presence_of :uuid, :description, :num_vcpus_allocated,
                        :memory_allocated_in_mb, :memory_allocated, :vnic_mac_addr

  acts_as_xapian :texts => [ :uuid, :description, :vnic_mac_addr, :state ],
                 :terms => [ [ :search_users, 'U', "search_users" ] ]

  BOOT_DEV_HD          = "hd"
  BOOT_DEV_NETWORK     = "network"
  BOOT_DEV_CDROM       = "cdrom"
  BOOT_DEV_FIELDS      = [ BOOT_DEV_HD, BOOT_DEV_NETWORK, BOOT_DEV_CDROM ]

  NEEDS_RESTART_FIELDS = [:uuid, 
                          :num_vcpus_allocated,
                          :memory_allocated,
                          :vnic_mac_addr]

  STATE_PENDING        = "pending"
  STATE_CREATING       = "creating"
  STATE_RUNNING        = "running"

  STATE_UNREACHABLE    = "unreachable"

  STATE_STOPPING       = "stopping"
  STATE_STOPPED        = "stopped"
  STATE_STARTING       = "starting"

  STATE_SUSPENDING     = "suspending"
  STATE_SUSPENDED      = "suspended"
  STATE_RESUMING       = "resuming"

  STATE_SAVING         = "saving"
  STATE_SAVED          = "saved"
  STATE_RESTORING      = "restoring"

  STATE_MIGRATING      = "migrating"

  STATE_CREATE_FAILED  = "create_failed"
  STATE_INVALID        = "invalid"

  RUNNING_STATES       = [STATE_RUNNING,
                          STATE_SUSPENDED,
                          STATE_STOPPING,
                          STATE_STARTING,
                          STATE_SUSPENDING,
                          STATE_RESUMING,
                          STATE_SAVING,
                          STATE_RESTORING,
                          STATE_MIGRATING]

  EFFECTIVE_STATE = {  STATE_PENDING       => STATE_PENDING,
                       STATE_UNREACHABLE   => STATE_UNREACHABLE,
                       STATE_CREATING      => STATE_STOPPED, 
                       STATE_RUNNING       => STATE_RUNNING,
                       STATE_STOPPING      => STATE_STOPPED,
                       STATE_STOPPED       => STATE_STOPPED,
                       STATE_STARTING      => STATE_RUNNING,
                       STATE_SUSPENDING    => STATE_SUSPENDED,
                       STATE_SUSPENDED     => STATE_SUSPENDED,
                       STATE_RESUMING      => STATE_RUNNING,
                       STATE_SAVING        => STATE_SAVED,
                       STATE_SAVED         => STATE_SAVED,
                       STATE_RESTORING     => STATE_RUNNING,
                       STATE_MIGRATING     => STATE_RUNNING,
                       STATE_CREATE_FAILED => STATE_CREATE_FAILED}
  TASK_STATE_TRANSITIONS = []

  def get_hardware_pool
    pool = vm_resource_pool
    pool = pool.get_hardware_pool if pool
    pool
  end
  def storage_volume_ids
    storage_volumes.collect {|x| x.id }
  end

  def storage_volume_ids=(ids)
    @storage_volumes_pending = ids.collect{|x| StorageVolume.find(x) }
  end

  def memory_allocated_in_mb
    kb_to_mb(memory_allocated)
  end
  def memory_allocated_in_mb=(mem)
    self[:memory_allocated]=(mb_to_kb(mem))
  end

  def memory_used_in_mb
    kb_to_mb(memory_used)
  end
  def memory_used_in_mb=(mem)
    self[:memory_used]=(mb_to_kb(mem))
  end

  def get_pending_state
    pending_state = state
    pending_state = EFFECTIVE_STATE[state] if pending_state
    tasks.queued.each do |task|
      return STATE_INVALID unless VmTask::ACTIONS[task.action][:start] == pending_state
      pending_state = VmTask::ACTIONS[task.action][:success]
    end
    return pending_state
  end

  def consuming_resources?
    RUNNING_STATES.include?(state)
  end

  def pending_resource_consumption?
    RUNNING_STATES.include?(get_pending_state)
  end

  def get_action_list(user=nil)
    # return empty list rather than nil
    return_val = VmTask.valid_actions_for_vm_state(get_pending_state, self, user) || []
    # filter actions based on quota
    unless resources_for_start?
      return_val = return_val - [VmTask::ACTION_START_VM, VmTask::ACTION_RESTORE_VM]
    end
    return_val
  end

  def get_action_hash(user=nil)
    actions = {}
    get_action_list(user).each do |action|
      actions[action] = VmTask::ACTIONS[action]
    end
    actions
  end

  # these resource checks are made at VM start/restore time
  # use pending here by default since this is used for queueing VM
  # creation/start operations
  #taskomatic should set use_pending_values to false
  def resources_for_start?(use_pending_values = true)
    return_val = true
    resources = vm_resource_pool.available_resources_for_vm(self, use_pending_values)
    return_val = false unless not(memory_allocated) or resources[:memory].nil? or memory_allocated <= resources[:memory]
    return_val = false unless not(num_vcpus_allocated) or resources[:cpus].nil? or num_vcpus_allocated <= resources[:cpus]
    return_val = false unless resources[:nics].nil? or resources[:nics] >= 1
    return_val = false unless (resources[:vms].nil? or resources[:vms] >= 1)

    # no need to enforce storage here since starting doesn't increase storage allocation
    return return_val
  end

  def queue_action(user, action, data = nil)
    return false unless get_action_list.include?(action)
    task = VmTask.new({ :user    => user,
                        :vm_id   => id,
                        :action  => action,
                        :args    => data,
                        :state   => Task::STATE_QUEUED})
    task.save!
    return true
  end

  def has_console
    (state == Vm::STATE_RUNNING ) and host and vnc_port
  end

  def display_name
    description
  end
  def display_class
    "VM"
  end

  def search_users
    vm_resource_pool.search_users
  end

  protected
  def validate
    resources = vm_resource_pool.max_resources_for_vm(self)
    # FIXME: what should memory min/max be?
    errors.add("memory_allocated_in_mb", "must be at least 256 MB") unless not(memory_allocated_in_mb) or memory_allocated_in_mb >=256
    # FIXME: what should cpu min/max
    errors.add("num_vcpus_allocated", "must be between 1 and 16") unless (num_vcpus_allocated >=1 and num_vcpus_allocated <= 16)
    errors.add("memory_allocated_in_mb", "violates quota") unless not(memory_allocated) or resources[:memory].nil? or memory_allocated <= resources[:memory]
    errors.add("num_vcpus_allocated", "violates quota") unless not(num_vcpus_allocated) or resources[:cpus].nil? or num_vcpus_allocated <= resources[:cpus]
    errors.add_to_base("No available nics in quota") unless resources[:nics].nil? or resources[:nics] >= 1
    # no need to validate VM limit here
    # need to enforce storage differently since obj is saved first
    storage_size = 0
    @storage_volumes_pending.each { |volume| storage_size += volume.size } if @storage_volumes_pending if defined? @storage_volumes_pending
    errors.add("storage_volumes", "violates quota") unless resources[:storage].nil? or storage_size <= resources[:storage]
    if errors.empty? and defined? @storage_volumes_pending
      self.storage_volumes=@storage_volumes_pending
      @storage_volumes_pending = []
    end
  end

end
