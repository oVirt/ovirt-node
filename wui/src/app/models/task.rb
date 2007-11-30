class Task < ActiveRecord::Base
  belongs_to :user
  belongs_to :vm

  ACTION_CREATE_VM   = "create_vm"

  ACTION_START_VM    = "start_vm"
  ACTION_SHUTDOWN_VM = "shutdown_vm"

  ACTION_SUSPEND_VM  = "suspend_vm"
  ACTION_RESUME_VM   = "resume_vm"

  ACTION_SAVE_VM     = "save_vm"
  ACTION_RESTORE_VM  = "restore_vm"

  STATE_QUEUED       = "queued"
  STATE_RUNNING      = "running"
  STATE_FINISHED     = "finished"
  STATE_PAUSED       = "paused"
  STATE_FAILED       = "failed"

end
