class Task < ActiveRecord::Base
  belongs_to :user
  belongs_to :vm

  ACTION_INSTALL_VIRT  = "install_virt"
  ACTION_DESTROY_VIRT  = "destroy_virt"
  ACTION_DELETE_VIRT   = "delete_virt"

  ACTION_START_VIRT    = "start_virt"
  ACTION_SHUTDOWN_VIRT = "shutdown_virt"

  ACTION_PAUSE_VIRT    = "pause_virt"
  ACTION_UNPAUSE_VIRT  = "unpause_virt"
  ACTION_TEST          = "test"

  ACTION_SAVE_VIRT     = "save_virt"
  ACTION_RESTORE_VIRT  = "restore_virt"

  STATE_QUEUED         = "queued"
  STATE_RUNNING        = "running"
  STATE_FINISHED       = "finished"
  STATE_PAUSED         = "paused"
  STATE_FAILED         = "failed"

end
