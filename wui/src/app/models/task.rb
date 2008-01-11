class Task < ActiveRecord::Base
  belongs_to :vm

  ACTION_CREATE_VM   = "create_vm"

  ACTION_START_VM    = "start_vm"
  ACTION_SHUTDOWN_VM = "shutdown_vm"

  ACTION_SUSPEND_VM  = "suspend_vm"
  ACTION_RESUME_VM   = "resume_vm"

  ACTION_SAVE_VM     = "save_vm"
  ACTION_RESTORE_VM  = "restore_vm"

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

  STATE_QUEUED       = "queued"
  STATE_RUNNING      = "running"
  STATE_FINISHED     = "finished"
  STATE_PAUSED       = "paused"
  STATE_FAILED       = "failed"
  STATE_CANCELED     = "canceled"

  COMPLETED_STATES = [STATE_FINISHED, STATE_FAILED, STATE_CANCELED]
  WORKING_STATES   = [STATE_QUEUED, STATE_RUNNING, STATE_PAUSED]

  def cancel
    self[:state] = STATE_CANCELED
    save
  end

  def self.working_tasks(user = nil)
    self.tasks_for_states(Task::WORKING_STATES, user)
  end

  def self.completed_tasks(user = nil)
    self.tasks_for_states(Task::COMPLETED_STATES, user)
  end

  def self.tasks_for_states(state_array, user = nil)
    conditions = state_array.collect {|x| "state='#{x}'"}.join(" or ")
    conditions = "(#{conditions}) and user='#{user}'"
    Task.find(:all, :conditions => conditions)
  end

end
