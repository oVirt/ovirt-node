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

  # a hash of task actions which point to a hash which define valid state transitions
  ACTIONS = { ACTION_CREATE_VM   => { :label => "Create VM",
                                      :start => Vm::STATE_PENDING,
                                      :running => Vm::STATE_CREATING,
                                      :success => Vm::STATE_STOPPED,
                                      :failure => Vm::STATE_CREATE_FAILED},
              ACTION_START_VM    => { :label => "Start VM",
                                      :start => Vm::STATE_STOPPED,
                                      :running => Vm::STATE_STARTING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_STOPPED}, 
              ACTION_SHUTDOWN_VM => { :label => "Shutdown VM",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_STOPPING,
                                      :success => Vm::STATE_STOPPED,
                                      :failure => Vm::STATE_RUNNING}, 
              ACTION_SUSPEND_VM  => { :label => "Suspend VM",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_SUSPENDING,
                                      :success => Vm::STATE_SUSPENDED,
                                      :failure => Vm::STATE_RUNNING}, 
              ACTION_RESUME_VM   => { :label => "Resume VM",
                                      :start => Vm::STATE_SUSPENDED,
                                      :running => Vm::STATE_RESUMING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_SUSPENDED},
              ACTION_SAVE_VM     => { :label => "Save VM",
                                      :start => Vm::STATE_RUNNING,
                                      :running => Vm::STATE_SAVING,
                                      :success => Vm::STATE_SAVED,
                                      :failure => Vm::STATE_RUNNING},
              ACTION_RESTORE_VM  => { :label => "Restore VM",
                                      :start => Vm::STATE_SAVED,
                                      :running => Vm::STATE_RESTORING,
                                      :success => Vm::STATE_RUNNING,
                                      :failure => Vm::STATE_SAVED} }

  VALID_ACTIONS_PER_VM_STATE = {  Vm::STATE_PENDING       => [ACTION_CREATE_VM],
                                  Vm::STATE_RUNNING       => [ACTION_SHUTDOWN_VM,
                                                              ACTION_SUSPEND_VM,
                                                              ACTION_SAVE_VM],
                                  Vm::STATE_STOPPED       => [ACTION_START_VM],
                                  Vm::STATE_SUSPENDED     => [ACTION_RESUME_VM],
                                  Vm::STATE_SAVED         => [ACTION_RESTORE_VM],
                                  Vm::STATE_CREATE_FAILED => [],
                                  Vm::STATE_INVALID       => []}

end
