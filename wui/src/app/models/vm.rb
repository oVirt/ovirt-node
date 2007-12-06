require 'util/ovirt'

class Vm < ActiveRecord::Base
  belongs_to :user
  belongs_to :host
  has_many :tasks, :dependent => :destroy, :order => "id DESC"
  has_and_belongs_to_many :storage_volumes
  validates_presence_of :uuid, :description, :num_vcpus_allocated,
                        :memory_allocated, :vnic_mac_addr

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
    # return empty list rather than nil
    Task::VALID_ACTIONS_PER_VM_STATE[get_pending_state] || []
  end

  def get_action_and_label_list
    get_action_list.collect do |action|
      [Task::ACTIONS[action][:label], action]
    end
  end

  protected
  def validate
    @storage_volumes_pending = [] unless defined? @storage_volumes_pending
    resources = user.user_quota.available_resources_for_vm(self)
    errors.add("memory_allocated_in_mb", "violates user quota") unless not(memory_allocated) or memory_allocated <= resources[:memory]
    # need to enforce storage differently since obj is saved first
    storage_size = 0
    @storage_volumes_pending.each { |volume| storage_size += volume.size } if @storage_volumes_pending
    
    errors.add("storage_volumes", "violates user quota") unless storage_size <= resources[:storage]
    errors.add("num_vcpus_allocated", "violates user quota") unless not(num_vcpus_allocated) or num_vcpus_allocated <= resources[:cpus]
    errors.add_to_base("No available nics in user quota") unless resources[:nics] >= 1
    if errors.empty? 
      self.storage_volumes=@storage_volumes_pending
      @storage_volumes_pending = []
    end
  end

end
