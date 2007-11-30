class Vm < ActiveRecord::Base
  belongs_to :user
  belongs_to :host
  has_many :tasks, :dependent => :destroy
  has_and_belongs_to_many :storage_volumes

  NEEDS_RESTART_FIELDS = [:uuid, 
                          :num_vcpus_allocated,
                          :memory_allocated,
                          :vnic_mac_addr]

  STATE_PENDING    = "pending"
  STATE_CREATING   = "creating"
  STATE_RUNNING    = "running"

  STATE_STOPPING   = "stopping"
  STATE_STOPPED    = "stopped"
  STATE_STARTING   = "starting"

  STATE_SUSPENDING = "suspending"
  STATE_SUSPENDED  = "suspended"
  STATE_RESUMING   = "resuming"

  STATE_SAVING     = "saving"
  STATE_SAVED      = "saved"
  STATE_RESTORING  = "restoring"

  STATE_DELETING   = "deleting"
  STATE_MIGRATING  = "migrating"
  STATE_UNKNOWN    = "unknown"

end
