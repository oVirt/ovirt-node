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

class VmTask < Task
  belongs_to :vm

  ACTION_CREATE_VM   = "create_vm"

  ACTION_START_VM    = "start_vm"
  ACTION_SHUTDOWN_VM = "shutdown_vm"

  ACTION_SUSPEND_VM  = "suspend_vm"
  ACTION_RESUME_VM   = "resume_vm"

  ACTION_SAVE_VM     = "save_vm"
  ACTION_RESTORE_VM  = "restore_vm"

  ACTION_UPDATE_STATE_VM = "update_state_vm"

  # for migrate VM action, args provides the optional target host
  ACTION_MIGRATE_VM  = "migrate_vm"

  PRIV_OBJECT_VM_POOL = "vm_resource_pool"
  PRIV_OBJECT_HW_POOL = "get_hardware_pool"


  # a hash of task actions which point to a hash which define valid state transitions
  ACTIONS = { ACTION_CREATE_VM   => { :label => "Create",
                                      :icon  => "icon_start.png",
                                      :start => Vm::STATE_PENDING,
                                      :running => Vm::STATE_CREATING,
                                      :success => Vm::STATE_STOPPED,
                                      :failure => Vm::STATE_CREATE_FAILED,
                                      :privilege => [Permission::PRIV_MODIFY,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_START_VM    => { :label => "Start",
                                      :icon  => "icon_start.png",
                                      :start => Vm::STATE_STOPPED,
                                      :running => Vm::STATE_STARTING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_STOPPED,
                                      :privilege => [Permission::PRIV_VM_CONTROL,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_SHUTDOWN_VM => { :label => "Shutdown",
                                      :icon  => "icon_x.png",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_STOPPING,
                                      :success => Vm::STATE_STOPPED,
                                      :failure => Vm::STATE_RUNNING,
                                      :privilege => [Permission::PRIV_VM_CONTROL,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_SUSPEND_VM  => { :label => "Suspend",
                                      :icon  => "icon_suspend.png",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_SUSPENDING,
                                      :success => Vm::STATE_SUSPENDED,
                                      :failure => Vm::STATE_RUNNING,
                                      :privilege => [Permission::PRIV_VM_CONTROL,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_RESUME_VM   => { :label => "Resume",
                                      :icon  => "icon_start.png",
                                      :start => Vm::STATE_SUSPENDED,
                                      :running => Vm::STATE_RESUMING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_SUSPENDED,
                                      :privilege => [Permission::PRIV_VM_CONTROL,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_SAVE_VM     => { :label => "Save",
                                      :icon  => "icon_save.png",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_SAVING,
                                      :success => Vm::STATE_SAVED,
                                      :failure => Vm::STATE_RUNNING,
                                      :privilege => [Permission::PRIV_VM_CONTROL,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_RESTORE_VM  => { :label => "Restore",
                                      :icon  => "icon_restore.png",
                                      :start => Vm::STATE_SAVED,
                                      :running => Vm::STATE_RESTORING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_SAVED,
                                      :privilege => [Permission::PRIV_VM_CONTROL,
                                                     PRIV_OBJECT_VM_POOL]},
              ACTION_MIGRATE_VM  => { :label => "Migrate",
                                      :icon  => "icon_restore.png",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_MIGRATING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_RUNNING,
                                      :privilege => [Permission::PRIV_MODIFY,
                                                     PRIV_OBJECT_HW_POOL],
                                      :popup_action => 'migrate'} }

  def self.valid_actions_for_vm_state(state, vm=nil, user=nil)
    actions = []
    ACTIONS.each do |action, hash|
      if hash[:start] == state
        add_action = true
        print "vm: #{vm}\n user: #{user}\n"
        if (vm and user)
          pool = vm.send(hash[:privilege][1])
          print "pool: #{pool}\n privilege: #{hash[:privilege][1]}\n"
          add_action = pool ? pool.has_privilege(user, hash[:privilege][0]) : false
        end
        print "add_action: #{add_action}\n"
        actions << action if add_action
      end
    end
    actions
  end

  def self.action_label(action)
    return ACTIONS[action][:label]
  end
  def self.action_icon(action)
    return ACTIONS[action][:icon]
  end
  def self.label_and_action(action)
    return [action_label(action), action, action_icon(action)]
  end
end
