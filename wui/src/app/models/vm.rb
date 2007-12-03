class Vm < ActiveRecord::Base
  belongs_to :user
  belongs_to :host
  has_many :tasks, :dependent => :destroy, :order => "id DESC"
  has_and_belongs_to_many :storage_volumes

  NEEDS_RESTART_FIELDS = [:uuid, 
                          :num_vcpus_allocated,
                          :memory_allocated,
                          :vnic_mac_addr]

  STATE_PENDING       = "pending"
  STATE_CREATING      = "creating"
  STATE_RUNNING       = "running"

  STATE_STOPPING      = "stopping"
  STATE_STOPPED       = "stopped"
  STATE_STARTING      = "starting"

  STATE_SUSPENDING    = "suspending"
  STATE_SUSPENDED     = "suspended"
  STATE_RESUMING      = "resuming"

  STATE_SAVING        = "saving"
  STATE_SAVED         = "saved"
  STATE_RESTORING     = "restoring"
  STATE_CREATE_FAILED = "create_failed"
  STATE_INVALID       = "invalid"

  VALID_ACTIONS_PER_STATE = {  STATE_PENDING       => [Task::ACTION_CREATE_VM],
                               STATE_RUNNING       => [Task::ACTION_SHUTDOWN_VM,
                                                       Task::ACTION_SUSPEND_VM,
                                                       Task::ACTION_SAVE_VM],
                               STATE_STOPPED       => [Task::ACTION_START_VM],
                               STATE_SUSPENDED     => [Task::ACTION_RESUME_VM],
                               STATE_SAVED         => [Task::ACTION_RESTORE_VM],
                               STATE_CREATE_FAILED => []}

  EFFECTIVE_STATE = {  STATE_PENDING       => STATE_PENDING,
                       STATE_CREATING      => STATE_RUNNING, 
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
                       STATE_CREATE_FAILED => STATE_CREATE_FAILED}
  TASK_STATE_TRANSITIONS = []

  def get_pending_state
    pending_state = state
    pending_state = EFFECTIVE_STATE[state] if pending_state
    get_queued_tasks.each do |task|
      return STATE_INVALID unless Task::ACTIONS[task.action][:start] == pending_state
      pending_state = Task::ACTIONS[task.action][:success]
    end
    return pending_state
  end

  def get_queued_tasks(state=nil)
    get_tasks(Task::STATE_QUEUED)
  end

  def get_tasks(state=nil)
    conditions = "vm_id = '#{id}'"
    conditions += " AND state = '#{Task::STATE_QUEUED}'" if state
    Task.find(:all, 
              :conditions => conditions,
              :order => "id")
  end    

  def get_action_list
    VALID_ACTIONS_PER_STATE[get_pending_state]
  end

  def get_action_and_label_list
    get_action_list.collect do |action|
      [Task::ACTIONS[action][:label], action]
    end
  end
end
